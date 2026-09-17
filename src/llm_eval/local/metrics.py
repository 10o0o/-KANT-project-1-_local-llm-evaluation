import csv
import math
import subprocess
from datetime import UTC, datetime
from llm_eval.local.server import find_server_pid

LOAD_REASON = "Persistent llama.cpp does not expose per-request model load duration."


def now():
    return datetime.now(UTC).isoformat()



def observation(value=None, reason=None, **details):
    return {"value": value, "reason": reason, **details}



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



def safe_memory(pid, phase, model=None):
    try:
        if pid is None:
            pid = find_server_pid(model)
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
