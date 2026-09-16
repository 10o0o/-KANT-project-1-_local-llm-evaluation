"""Generation completion compatibility and atomic JSON persistence."""

import json
import os
import tempfile
from pathlib import Path


def write_json(path: Path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, default=str)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def generation_complete(record):
    if not isinstance(record, dict):
        return False
    call = record.get("call")
    if not isinstance(call, dict) or call.get("status") not in {"success", "error"}:
        return False
    if "record_complete" in record:
        return record["record_complete"] is True and (
            call["status"] == "error" or (
                isinstance(record.get("generation"), dict)
                and "extracted_code" in record
                and (record["extracted_code"] is None or isinstance(record["extracted_code"], str))
            )
        )
    # Only legacy local records lack a completion marker.
    experiment = record.get("experiment")
    if not isinstance(experiment, dict) or experiment.get("type") != "benchmark":
        return False
    if call["status"] == "error":
        return True
    judge = record.get("judge")
    return isinstance(judge, dict) and judge.get("status") in {
        "AC", "WA", "TLE", "RE", "NO_CODE",
    }
