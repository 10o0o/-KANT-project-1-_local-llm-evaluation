import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


def owns_server_port(pid):
    """Prove this process owns the listening socket, not only a live PID."""
    sockets = set()
    for fd in (Path("/proc") / str(pid) / "fd").iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith("socket:["):
            sockets.add(target[8:-1])
    for table in ("tcp", "tcp6"):
        for line in (Path("/proc/net") / table).read_text().splitlines()[1:]:
            fields = line.split()
            if (
                fields[3] == "0A"
                and int(fields[1].split(":")[1], 16) == 8080
                and fields[9] in sockets
            ):
                return True
    return False



def find_server_pid(model):
    """Find the local listening llama-server, without a saved session record."""
    matches = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc / "exe").resolve(strict=True).name != "llama-server":
                continue
            args = (proc / "cmdline").read_bytes().decode().rstrip("\0").split("\0")
            if model is not None and (
                "--alias" not in args or args[args.index("--alias") + 1] != model
            ):
                continue
            pid = int(proc.name)
            if owns_server_port(pid):
                matches.append(pid)
        except (OSError, ValueError, IndexError, UnicodeError):
            continue
    return matches[0] if len(matches) == 1 else None



def port_busy():
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", 8080))
        except OSError:
            return True
    return False



def http_json(path):
    # Local readiness must not use a system HTTP proxy.
    with build_opener(ProxyHandler({})).open("http://127.0.0.1:8080" + path, timeout=2) as response:
        return json.load(response)



def actual_argv(pid):
    return (Path("/proc") / str(pid) / "cmdline").read_bytes().decode().rstrip("\0").split("\0")



def wait_ready(process, model, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{model} 서버 조기 종료: {process.returncode}")
        try:
            healthy = http_json("/health").get("status") == "ok"
            if healthy:
                models = http_json("/v1/models").get("data", [])
                if [item.get("id") for item in models] != [model]:
                    raise RuntimeError(f"서버 모델 별칭 불일치: 기대값 {model}")
                if not owns_server_port(process.pid):
                    raise RuntimeError("시작한 서버 PID가 8080 포트를 소유하지 않습니다. 셸의 exec를 확인하세요.")
                return actual_argv(process.pid)
        except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    raise RuntimeError(f"{model} 서버 준비 시간 초과 ({timeout:g}초)")



def stop_owned(process):
    """A live Popen is our child, launched in a new session; never discover-and-kill."""
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)
        raise RuntimeError(f"소유 프로세스 PID {process.pid} 종료 지연: 강제 종료 후 예약 중단")



def wait_port_free(timeout=10):
    deadline = time.monotonic() + timeout
    while port_busy():
        if time.monotonic() >= deadline:
            raise RuntimeError("서버 종료 후에도 8080 포트가 사용 중입니다.")
        time.sleep(0.2)
