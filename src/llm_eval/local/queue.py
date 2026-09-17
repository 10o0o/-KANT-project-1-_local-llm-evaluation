"""Local generation queue; owns only the server and clients it starts."""

import argparse
import hashlib
import math
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_eval.local.runner import inspect_existing, request_conditions
from llm_eval.shared.paths import generation_dir
from llm_eval.shared.problems import load_problems
from llm_eval.shared.processes import (
    WorkloadLease,
    ancestor_pids,
    ensure_workload_safe,
    workload,
)
from llm_eval.shared.storage import write_json
from llm_eval.local.server import port_busy, wait_ready, stop_owned, wait_port_free

MODELS = ("qwen36", "gemma4")
def timestamp():
    return datetime.now(UTC).isoformat()


def ancestors():
    return ancestor_pids()


def check_idle(proc_root=Path("/proc")):
    ensure_workload_safe("queue", proc_root, excluded_pids=ancestors())
    if port_busy():
        raise RuntimeError("127.0.0.1:8080 포트가 사용 중입니다.")


def inspect_round(root, problems, model, number):
    missing = []
    for problem in problems:
        request, config = request_conditions(root, problem)
        folder = generation_dir(root, problem["name"], model, number)
        record = inspect_existing(folder, problem, model, number, request, config)
        if record is None:
            missing.append(problem["id"])
        elif record["call"]["status"] != "success":
            raise RuntimeError(f"저장된 호출 실패: {folder}; 자동 재시도하지 않습니다.")
    return missing


def inspect_all(root, problems):
    return {(model, number): inspect_round(root, problems, model, number)
            for model in MODELS for number in (1, 2)}


@contextmanager
def queue_lock(folder):
    folder = Path(folder).resolve()
    root = folder.parent.parent if folder.name == "local_queue" and folder.parent.name == "logs" else folder
    with workload(root, "queue") as lease:
        yield lease


class LocalQueue:
    def __init__(self, root, logs, timeout, lease: WorkloadLease | None = None):
        self.root, self.logs, self.timeout = root, logs, timeout
        self.lease = lease
        self.server = None
        self.client = None
        self.handles = []
        self.owned = []
        self.state = {"started_at": timestamp(), "finished_at": None, "status": "running", "stage": "preflight"}

    def event(self, stage, **details):
        self.state.update(stage=stage, **details)
        write_json(self.logs / "status.json", self.state)
        message = f"{timestamp()} {stage} {details}"
        print(message, flush=True)
        with (self.logs / "queue.log").open("a", encoding="utf-8") as stream:
            stream.write(message + "\n")

    def spawn(self, args, name, inherit_lock=False):
        handle = (self.logs / name).open("wb")
        self.handles.append(handle)
        # Register ownership before a pending interrupt can reach the handler.
        pending = []
        previous = {sig: signal.signal(sig, lambda signum, frame: pending.append(signum))
                    for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            lock_options = {}
            if inherit_lock:
                if self.lease is None:
                    raise RuntimeError("자식 작업에 전달할 저장소 잠금이 없습니다.")
                lock_options = {
                    "env": self.lease.child_env(),
                    "pass_fds": self.lease.child_pass_fds(),
                }
            process = subprocess.Popen(
                args,
                cwd=self.root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                restore_signals=True,
                **lock_options,
            )
            self.owned.append(process)
            return process
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            if pending:
                raise KeyboardInterrupt(f"signal {pending[0]}")

    def command(self, args, name):
        self.client = self.spawn(
            [sys.executable, "-u", *args], name, inherit_lock=True
        )
        while self.client.poll() is None:
            if self.server is not None and self.server.poll() is not None:
                raise RuntimeError("생성 도중 모델 서버가 종료됐습니다.")
            time.sleep(0.2)
        code = self.client.returncode
        self.client = None
        if code != 0:
            raise RuntimeError(f"실행 실패 ({code}): {name}")

    def start_server(self, model):
        script = self.root / "configs/llama.cpp" / f"{model}.sh"
        # Read at model transition, not when the queue was first started.
        content = script.read_bytes()
        snapshot = self.logs / f"{model}.server.sh"
        snapshot.write_bytes(content)
        subprocess.run(["bash", "-n", str(snapshot)], check=True, timeout=10,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if port_busy():
            raise RuntimeError("서버 시작 전 8080 포트 충돌")
        self.event("server_start", model=model, script_sha256=hashlib.sha256(content).hexdigest())
        self.server = self.spawn(["bash", str(snapshot)], f"{model}.server.log")
        argv = wait_ready(self.server, model, self.timeout)
        self.event("server_ready", model=model, server_pid=self.server.pid, server_argv=argv)

    def run_round(self, problems, model, number):
        remaining = inspect_round(self.root, problems, model, number)
        if remaining:
            self.event("generation", model=model, round=number, remaining=remaining)
            self.command(
                [
                    "scripts/run_local_benchmark.py",
                    "--model",
                    model,
                    "--problems",
                    "all",
                    "--round",
                    str(number),
                ],
                f"{model}.round_{number}.log",
            )
        if inspect_round(self.root, problems, model, number):
            raise RuntimeError(f"{model} round {number}: 종료 후 미완료 기록")
        self.event("round_complete", model=model, round=number)

    def run_model(self, problems, work, model):
        if not any(work[(model, number)] for number in (1, 2)):
            self.event("model_already_complete", model=model)
            return
        check_idle()
        self.start_server(model)
        self.event("warmup", model=model)
        self.command(["scripts/run_warmup.py", "--model", model], f"{model}.warmup.log")
        for number in (1, 2):
            self.run_round(problems, model, number)
        self.event("server_stopping", model=model)
        stop_owned(self.server)
        self.server = None
        wait_port_free()

    def cleanup(self):
        errors = []
        # Ignore repeated interrupts while owned children are being reaped.
        previous = {
            signal_number: signal.signal(signal_number, signal.SIG_IGN)
            for signal_number in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            processes = {
                id(process): process
                for process in [self.client, self.server, *self.owned]
                if process is not None
            }
            for process in processes.values():
                try:
                    stop_owned(process)
                except Exception as exc:
                    errors.append(str(exc))
            for handle in self.handles:
                handle.close()
            if errors:
                self.state.update(status="error", cleanup_errors=errors)
            self.state["finished_at"] = timestamp()
            self.event("finished")
        finally:
            for signal_number, handler in previous.items():
                signal.signal(signal_number, handler)
        return errors

    def execute(self, problems, work):
        try:
            self.event("preflight_complete", remaining={f"{m}/round_{n}": ids for (m, n), ids in work.items()},
                       generation_request=request_conditions(self.root, problems[0])[1])
            for model in MODELS:
                self.run_model(problems, work, model)
            self.state["status"] = "completed"
        except BaseException as exc:
            self.state["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
            self.state["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            errors = self.cleanup()
            if errors and sys.exc_info()[0] is None:
                raise RuntimeError("; ".join(errors))


def run_queue(root, timeout=900):
    root = root.resolve()
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("startup timeout은 양수여야 합니다.")
    # The local lane covers queue children and excludes judging; Cloud has an
    # independent lane and may run concurrently.
    with workload(root, "queue") as lease:
        problems = load_problems(root)
        if len(problems) != 10 or len({p['id'] for p in problems}) != 10:
            raise ValueError("예약은 서로 다른 기존 10문제 × 2모델 × 2회차를 대상으로 합니다.")
        work = inspect_all(root, problems)
        session = root / "logs/local_queue" / (datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ") + "_" + uuid4().hex[:8])
        session.mkdir(parents=True)
        print(f"예약 로그: {session}", flush=True)
        queue = LocalQueue(root, session, timeout, lease)
        queue.execute(problems, work)
        return session


def main(root, argv=None):
    parser = argparse.ArgumentParser(description="Qwen·Gemma 두 회차 로컬 생성만 순차 실행")
    parser.add_argument("--startup-timeout-seconds", type=float, default=900)
    args = parser.parse_args(argv)
    def interrupt(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")
    previous = {s: signal.signal(s, interrupt) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        run_queue(root, args.startup_timeout_seconds)
    except KeyboardInterrupt:
        raise SystemExit("예약 중단: 로그와 기존 결과를 확인하세요.") from None
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"ABORT: {exc}") from None
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
