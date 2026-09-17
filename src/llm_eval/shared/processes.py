"""Cross-entrypoint workload exclusion and inherited lock ownership."""

import fcntl
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


WORKLOAD_FD_ENV = "LLM_EVAL_WORKLOAD_LOCK_FD"
WORKLOAD_KINDS = frozenset({"local", "warmup", "cloud", "queue", "judge"})
SCRIPT_KINDS = {
    "run_benchmark.py": "local",
    "run_local_benchmark.py": "local",
    "run_warmup.py": "warmup",
    "run_cloud_benchmark.py": "cloud",
    "run_local_queue.py": "queue",
    "run_judge.py": "judge",
    "run_batch_judge.py": "judge",
    "check_candidate.py": "judge",
}
MODULE_KINDS = {
    "llm_eval.local.cli": "local",
    "llm_eval.cloud.cli": "cloud",
    "llm_eval.local.queue": "queue",
    "llm_eval.judging.batch": "judge",
}


def workload_lock_path(root: Path) -> Path:
    return Path(root).resolve() / "logs" / ".workload.lock"


def ancestor_pids(proc_root: Path = Path("/proc")) -> set[int]:
    """Return this process and its ancestors for child adoption checks."""
    result = {os.getpid()}
    pid = os.getppid()
    while pid > 1 and pid not in result:
        result.add(pid)
        try:
            fields = (proc_root / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
            pid = int(fields[1])
        except (FileNotFoundError, ProcessLookupError):
            break
        except (OSError, ValueError, IndexError) as exc:
            raise RuntimeError(f"프로세스 계보를 확인할 수 없습니다: PID {pid}") from exc
    return result


def _runner_kind(argv: list[str]) -> str | None:
    executable = Path(argv[0]).name
    if not (executable.startswith("python") or executable == "uv") or "-c" in argv:
        return None
    for argument in argv[1:]:
        kind = SCRIPT_KINDS.get(Path(argument).name)
        if kind is not None:
            return kind
    if "-m" in argv:
        index = argv.index("-m") + 1
        if index < len(argv):
            return MODULE_KINDS.get(argv[index])
    return None


def active_workloads(
    proc_root: Path = Path("/proc"), excluded_pids: set[int] | None = None
) -> list[dict]:
    """Find benchmark runners and servers, including those in other checkouts."""
    proc_root = Path(proc_root)
    if not proc_root.is_dir():
        raise RuntimeError("프로세스 확인은 Linux/WSL에서 지원합니다.")
    excluded = ancestor_pids(proc_root) if excluded_pids is None else set(excluded_pids)
    found = []
    for folder in proc_root.iterdir():
        if not folder.name.isdigit() or int(folder.name) in excluded:
            continue
        try:
            argv = [
                item.decode(errors="replace")
                for item in (folder / "cmdline").read_bytes().split(b"\0")
                if item
            ]
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            raise RuntimeError(f"프로세스 확인 권한 없음: PID {folder.name}") from exc
        if not argv:
            continue
        executable = Path(argv[0]).name
        kind = "server" if executable in {"llama-server", "llama-server.exe"} else _runner_kind(argv)
        if kind is not None:
            found.append(
                {"pid": int(folder.name), "kind": kind, "executable": executable}
            )
    return sorted(found, key=lambda item: item["pid"])


def ensure_workload_safe(
    kind: str,
    proc_root: Path = Path("/proc"),
    excluded_pids: set[int] | None = None,
) -> None:
    if kind not in WORKLOAD_KINDS:
        raise ValueError(f"지원하지 않는 작업 종류: {kind}")
    allowed = {"server"} if kind in {"local", "warmup"} else set()
    conflicts = [
        item
        for item in active_workloads(proc_root, excluded_pids)
        if item["kind"] not in allowed
    ]
    if conflicts:
        raise RuntimeError(f"실행 중인 벤치마크 작업이 있습니다: {conflicts}")


@dataclass(frozen=True)
class WorkloadLease:
    root: Path
    kind: str
    fd: int
    borrowed: bool

    def child_env(self, base: dict[str, str] | None = None) -> dict[str, str]:
        environment = dict(os.environ if base is None else base)
        environment[WORKLOAD_FD_ENV] = str(self.fd)
        return environment

    def child_pass_fds(self) -> tuple[int]:
        return (self.fd,)


def _validate_inherited_fd(root: Path, raw_fd: str) -> int:
    try:
        fd = int(raw_fd)
        if fd < 0:
            raise ValueError
        inherited = os.fstat(fd)
        expected = workload_lock_path(root).stat()
    except (OSError, ValueError) as exc:
        raise RuntimeError("상속된 작업 잠금 FD가 유효하지 않습니다.") from exc
    if (inherited.st_dev, inherited.st_ino) != (expected.st_dev, expected.st_ino):
        raise RuntimeError("상속된 작업 잠금 FD가 현재 저장소 잠금과 일치하지 않습니다.")
    probe = os.open(workload_lock_path(root), os.O_RDWR)
    try:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            fcntl.flock(probe, fcntl.LOCK_UN)
            raise RuntimeError("상속된 작업 잠금 FD가 잠금을 보유하지 않습니다.")
    finally:
        os.close(probe)
    # The probe proves a lock exists; this verifies this open file description owns it.
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError("상속 FD가 아닌 다른 실행이 작업 잠금을 보유하고 있습니다.") from exc
    return fd


@contextmanager
def workload(
    root: Path,
    kind: str,
    allow_inherited: bool = False,
):
    """Hold this repository's workload lock, or borrow its inherited FD."""
    root = Path(root).resolve()
    if kind not in WORKLOAD_KINDS:
        raise ValueError(f"지원하지 않는 작업 종류: {kind}")
    if allow_inherited and kind not in {"local", "warmup"}:
        raise ValueError("상속 잠금은 로컬 생성과 준비 호출에서만 허용됩니다.")

    inherited_value = os.environ.get(WORKLOAD_FD_ENV)
    if inherited_value is not None:
        if not allow_inherited:
            raise RuntimeError("이 작업은 상속된 작업 잠금을 사용할 수 없습니다.")
        fd = _validate_inherited_fd(root, inherited_value)
        ensure_workload_safe(kind)
        yield WorkloadLease(root, kind, fd, borrowed=True)
        return

    ensure_workload_safe(kind)
    path = workload_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as exc:
            raise RuntimeError("이미 다른 벤치마크 작업이 실행 중입니다.") from exc
        ensure_workload_safe(kind)
        yield WorkloadLease(root, kind, fd, borrowed=False)
    finally:
        try:
            if acquired:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
