"""Foreground launcher: no model request is made by this module."""

import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from llm_eval.runtime import (
    capture_environment,
    get_json,
    now,
    owns_server_port,
    port_in_use,
    safe_memory,
)


def write_record(path, record):
    # Unique files are published only after the whole JSON has been written.
    temporary = path.with_suffix(".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)  # fails rather than replacing an existing record
    finally:
        temporary.unlink()


def wait_ready(process, started, timeout):
    deadline = started + timeout
    while True:
        if process.poll() is not None:
            raise RuntimeError(
                f"Server exited before readiness (code {process.returncode})"
            )
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError("Server readiness deadline exceeded")
        try:
            healthy = (
                get_json("/health", timeout=min(0.5, remaining)).get("status") == "ok"
            )
        except (OSError, ValueError):
            healthy = False
        elapsed = time.perf_counter() - started
        if healthy and elapsed <= timeout and process.poll() is None:
            if not owns_server_port(process.pid):
                raise RuntimeError(
                    "Healthy endpoint is not owned by the launched server"
                )
            return elapsed
        time.sleep(min(0.5, max(0, deadline - time.perf_counter())))


def stop_owned(process, signum=signal.SIGTERM):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def start_model(project_root: Path, model: str, ready_timeout=600):
    if model not in {"qwen36", "gemma4"}:
        raise ValueError("Unknown model alias")
    if not math.isfinite(ready_timeout) or ready_timeout <= 0:
        raise ValueError("Readiness timeout must be a positive finite number")
    if port_in_use():
        raise RuntimeError(
            "127.0.0.1:8080 is already in use; existing process was not changed"
        )
    session_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{model}_{uuid4().hex[:12]}"
    directory = project_root / "results" / "environment" / session_id
    directory.mkdir(parents=True, exist_ok=False)
    environment_path = directory / "environment.json"
    log_path = directory / "server.log"
    process = None
    previous_handlers = {}
    interrupted = None
    result_code = 1

    def on_signal(signum, frame):
        nonlocal interrupted
        interrupted = signum
        raise KeyboardInterrupt

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[sig] = signal.signal(sig, on_signal)
    try:
        with log_path.open("x", encoding="utf-8") as log:
            print(f"Server log: {log_path}", flush=True)
            started = time.perf_counter()
            process = subprocess.Popen(
                ["bash", str(project_root / "configs" / "llama.cpp" / f"{model}.sh")],
                cwd=project_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            startup_seconds = wait_ready(process, started, ready_timeout)
            memory = safe_memory(process.pid, "server_ready")
            environment = capture_environment(
                process.pid,
                model,
                session_id,
                log_path,
                startup_seconds,
                memory,
            )
            if process.poll() is not None:
                raise RuntimeError("Server exited during environment capture")
            write_record(environment_path, environment)
            print(f"Ready. Use --environment {environment_path}", flush=True)
            print("Keep this terminal open; Ctrl-C stops only this server.", flush=True)
            result_code = process.wait()
    except KeyboardInterrupt:
        result_code = 128 + (interrupted or signal.SIGINT)
        if not environment_path.exists():
            write_record(
                environment_path,
                {
                    "session_id": session_id,
                    "model": model,
                    "status": "interrupted",
                    "observed_at": now(),
                },
            )
    except Exception as exc:  # noqa: BLE001 - preserve failure and always clean up owned child
        if not environment_path.exists():
            write_record(
                environment_path,
                {
                    "session_id": session_id,
                    "model": model,
                    "status": "failed",
                    "observed_at": now(),
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            )
        print(f"Startup failed: {type(exc).__name__}: {exc}", flush=True)
    finally:
        # Ignore repeated interrupts while cleaning up the owned process group.
        for sig in previous_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            stop_owned(process, interrupted or signal.SIGTERM)
            write_record(
                directory / "exit.json",
                {
                    "observed_at": now(),
                    "exit_code": result_code,
                    "server_returncode": process.returncode if process else None,
                },
            )
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
    return result_code
