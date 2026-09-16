"""Read-only runtime observations and binding to one local server session."""

import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

SERVER_URL = "http://127.0.0.1:8080"
LOAD_REASON = "Persistent llama.cpp does not expose per-request model load duration."


def now():
    return datetime.now(UTC).isoformat()


def observation(value=None, reason=None, **details):
    return {"value": value, "reason": reason, **details}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path):
    path = Path(path).resolve()
    before = path.stat()
    digest = sha256(path)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Artifact changed while hashing")
    return {
        "path": str(path),
        "filename": path.name,
        "size_bytes": after.st_size,
        "mtime_ns": after.st_mtime_ns,
        "sha256": digest,
        "device": after.st_dev,
        "inode": after.st_ino,
    }


def get_json(route, timeout=2):
    # Local observations must not go through an HTTP proxy.
    opener = build_opener(ProxyHandler({}))
    with opener.open(SERVER_URL + route, timeout=timeout) as response:
        return json.load(response)


def port_in_use():
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", 8080)) == 0


def process_identity(pid):
    proc = Path("/proc") / str(pid)
    fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    if fields[0] == "Z":
        raise ValueError("Server process is a zombie")
    return {
        "pid": pid,
        "start_ticks": fields[19],
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "executable": str((proc / "exe").resolve(strict=True)),
        "cmdline_sha256": hashlib.sha256((proc / "cmdline").read_bytes()).hexdigest(),
    }


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


def command_output(args):
    return subprocess.check_output(
        args, text=True, stderr=subprocess.DEVNULL, timeout=5
    ).strip()


def memory_mib(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Unavailable or invalid GPU memory")
    return result


def observe_memory(pid, phase):
    result = {
        "observed_at": now(),
        "phase": phase,
        "source": "nvidia-smi",
        "process": observation(
            reason="Process memory unavailable",
            unit="MiB",
            scope="server_process",
            pid=pid,
        ),
        "devices": observation(
            reason="Device memory unavailable", unit="MiB", scope="whole_device"
        ),
    }
    try:
        output = command_output(
            [
                "nvidia-smi",
                "--query-gpu=uuid,name,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ]
        )
        devices = []
        for row in csv.reader(output.splitlines()):
            uuid, name, used, total = (x.strip() for x in row)
            devices.append(
                {
                    "uuid": uuid,
                    "name": name,
                    "used_mib": memory_mib(used),
                    "total_mib": memory_mib(total),
                }
            )
        if devices:
            result["devices"] = observation(devices, unit="MiB", scope="whole_device")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result["devices"]["reason"] = f"Device query unavailable ({type(exc).__name__})"
    try:
        output = command_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ]
        )
        matches = []
        for row in csv.reader(output.splitlines()):
            process_pid, uuid, used = (x.strip() for x in row)
            if int(process_pid) == pid:
                matches.append({"gpu_uuid": uuid, "used_mib": memory_mib(used)})
        if matches:
            result["process"] = observation(
                sum(x["used_mib"] for x in matches),
                unit="MiB",
                scope="server_process",
                pid=pid,
                devices=matches,
            )
        else:
            result["process"]["reason"] = (
                "No matching server PID in nvidia-smi; WSL may not expose process memory or matching PIDs"
            )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result["process"]["reason"] = (
            f"Process query unavailable; no device-memory substitution ({type(exc).__name__})"
        )
    return result


def safe_memory(pid, phase):
    try:
        return observe_memory(pid, phase)
    except Exception as exc:  # noqa: BLE001 - optional observation must not lose a model response
        return {
            "observed_at": now(),
            "phase": phase,
            "source": "nvidia-smi",
            "process": observation(
                reason=f"Observation failed ({type(exc).__name__})",
                unit="MiB",
                scope="server_process",
            ),
            "devices": observation(
                reason="Observation failed", unit="MiB", scope="whole_device"
            ),
        }


def props_identity(props):
    return {
        "model_path": props.get("model_path"),
        "context_size": props.get("default_generation_settings", {}).get("n_ctx"),
        "total_slots": props.get("total_slots"),
        "build_info": props.get("build_info"),
    }


def log_observation(log, pattern, source):
    matches = re.findall(pattern, log, re.MULTILINE)
    return observation(
        matches[-1] if matches else None,
        None if matches else "Not found in server log",
        source=source,
    )


def process_arguments(pid):
    return (
        (Path("/proc") / str(pid) / "cmdline")
        .read_bytes()
        .decode()
        .rstrip("\0")
        .split("\0")
    )


def capture_environment(
    pid, model, session_id, log_path, startup_seconds, ready_memory
):
    proc = Path("/proc") / str(pid)
    argv = process_arguments(pid)
    # Only the known non-secret launcher options are copied to the manifest.
    allowed = {
        "--model",
        "--alias",
        "--host",
        "--port",
        "--ctx-size",
        "--n-predict",
        "--parallel",
        "--gpu-layers",
        "--n-cpu-moe",
        "--load-mode",
        "--flash-attn",
        "--temp",
        "--reasoning",
        "--reasoning-budget",
        "--threads",
        "--threads-batch",
        "--cache-ram",
        "--fit",
    }
    options = {}
    for i, arg in enumerate(argv[:-1]):
        if arg in allowed:
            options[arg] = argv[i + 1]
    if (
        options.get("--alias") != model
        or options.get("--host") != "127.0.0.1"
        or options.get("--port") != "8080"
    ):
        raise ValueError(
            "Launched server arguments do not match the selected model/endpoint"
        )
    raw_props = get_json("/props")
    props = props_identity(raw_props)
    models = get_json("/v1/models")
    if model not in [entry.get("id") for entry in models.get("data", [])]:
        raise ValueError("Server does not expose selected model alias")
    identity = process_identity(pid)
    if not owns_server_port(pid):
        raise ValueError("Launched process does not own the server port")
    model_path = Path(options["--model"])
    if not model_path.is_absolute():
        model_path = (proc / "cwd").resolve() / model_path
    observed_path = Path(props["model_path"])
    if not observed_path.is_absolute():
        observed_path = (proc / "cwd").resolve() / observed_path
    if observed_path.resolve() != model_path.resolve():
        raise ValueError("Server model path differs from command line")
    executable = Path(identity["executable"])
    runtime_root = (
        executable.parents[2]
        if executable.parent.name == "bin" and executable.parent.parent.name == "build"
        else None
    )
    try:
        if runtime_root is None:
            raise ValueError(
                "Executable is outside the expected source/build/bin layout"
            )
        source = {
            "root": str(runtime_root),
            "commit": command_output(
                ["git", "-C", str(runtime_root), "rev-parse", "HEAD"]
            ),
            "dirty": bool(
                command_output(
                    ["git", "-C", str(runtime_root), "status", "--porcelain"]
                )
            ),
            "association": "Checkout containing the binary; commit alone does not prove build provenance. See binary SHA-256 and server build_info.",
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        source = {
            "root": str(runtime_root) if runtime_root else None,
            "commit": None,
            "dirty": None,
            "reason": "Associated Git source metadata unavailable",
        }
    log = log_path.read_text(errors="replace")
    packages = {}
    for name in ("openai", "httpx"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    try:
        ram = (
            int(
                re.search(
                    r"^MemTotal:\s+(\d+)",
                    Path("/proc/meminfo").read_text(),
                    re.MULTILINE,
                )[1]
            )
            / 1024
        )
    except (OSError, TypeError, ValueError):
        ram = None
    try:
        cpu = re.search(
            r"^model name\s*:\s*(.+)$", Path("/proc/cpuinfo").read_text(), re.MULTILINE
        )
        cpu_name = cpu[1] if cpu else (platform.processor() or None)
    except OSError:
        cpu_name = platform.processor() or None
    return {
        "schema_version": 1,
        "session_id": session_id,
        "status": "ready",
        "model": model,
        "server_url": SERVER_URL,
        "observed_at": now(),
        "process": identity,
        "configured": {
            "arguments": options,
            "source": "live process command line; omitted options use runtime defaults",
        },
        "artifacts": {
            "model": file_identity(model_path),
            "binary": file_identity(identity["executable"]),
        },
        "source_checkout": source,
        "software": {
            "python": platform.python_version(),
            "packages": packages,
            "platform": platform.platform(),
        },
        "hardware": {
            "cpu": cpu_name,
            "logical_cpus": os.cpu_count(),
            "system_ram_mib": observation(
                ram,
                None if ram is not None else "MemTotal unavailable",
                source="/proc/meminfo (WSL guest)",
            ),
        },
        "observed": {
            "props": props,
            "raw_props": raw_props,
            "context_size": observation(
                props["context_size"],
                None if props["context_size"] is not None else "n_ctx unavailable",
                source="GET /props default_generation_settings.n_ctx",
            ),
            "quantization": log_observation(
                log, r"^.*(?:model ftype|file type)\s*=\s*(.+)$", "server.log"
            ),
            "gpu_offload": log_observation(
                log,
                r"^.*offloaded (\d+/\d+ layers to GPU).*$",
                "server.log; layer count is not MoE tensor placement or utilization",
            ),
            "placement_log": [
                line
                for line in log.splitlines()
                if re.search(
                    r"buffer size|offload|CPU_Mapped|CPU buffer|CUDA\d+ buffer", line
                )
            ],
            "server_startup_seconds": startup_seconds,
            "server_startup_definition": "Popen start to first healthy response; includes process initialization and readiness polling, excludes artifact hashing",
            "memory": ready_memory,
        },
    }


def load_environment(path, model, project_root):
    path = Path(path).resolve()
    raw = path.read_bytes()
    data = json.loads(raw)
    if (
        data.get("schema_version") != 1
        or data.get("status") != "ready"
        or data.get("model") != model
        or data.get("server_url") != SERVER_URL
    ):
        raise ValueError(
            "Environment must be a ready session for the selected model and local endpoint"
        )
    try:
        reference_path = str(path.relative_to(project_root.resolve()))
    except ValueError:
        reference_path = str(path)
    environment = {
        "data": data,
        "reference": {
            "session_id": data["session_id"],
            "path": reference_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "server_startup_seconds": data["observed"]["server_startup_seconds"],
        },
    }
    validate_environment(environment, model)
    return environment


def validate_environment(environment, model):
    data = environment["data"]
    if (
        data["model"] != model
        or process_identity(data["process"]["pid"]) != data["process"]
    ):
        raise ValueError("Environment model or live server process identity mismatch")
    if not owns_server_port(data["process"]["pid"]):
        raise ValueError("Recorded process no longer owns server port")
    for artifact in data["artifacts"].values():
        stat = Path(artifact["path"]).stat()
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != (
            artifact["device"],
            artifact["inode"],
            artifact["size_bytes"],
            artifact["mtime_ns"],
        ):
            raise ValueError("Runtime artifact changed since environment capture")
    if get_json("/health").get("status") != "ok":
        raise ValueError("Server is not ready")
    if props_identity(get_json("/props")) != data["observed"]["props"]:
        raise ValueError("Current server properties differ from recorded session")
    aliases = [item.get("id") for item in get_json("/v1/models").get("data", [])]
    if model not in aliases:
        raise ValueError("Current server model alias mismatch")


def measured_metrics(elapsed, usage, timings, memory):
    speed = timings.get("predicted_per_second")
    duration = timings.get("predicted_ms")

    def valid(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    reason = None
    if not valid(duration) or duration <= 0:
        speed, reason = None, "Missing, invalid or non-positive timings.predicted_ms"
    elif not valid(speed) or speed < 0:
        speed, reason = None, "Missing or invalid timings.predicted_per_second"
    return {
        "response_elapsed_seconds": elapsed,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "generation_tokens_per_second": speed,
        "generation_tokens_per_second_reason": reason,
        "generation_tokens_per_second_source": "llama.cpp timings.predicted_per_second",
        "prompt_tokens_reason": None
        if usage.get("prompt_tokens") is not None
        else "usage.prompt_tokens unavailable",
        "completion_tokens_reason": None
        if usage.get("completion_tokens") is not None
        else "usage.completion_tokens unavailable",
        "model_load_seconds": None,
        "model_load_reason": LOAD_REASON,
        "memory": memory,
    }
