import json
from pathlib import Path


def generation_dir(
    root: Path, problem_name: str, model: str, round_number: int
) -> Path:
    return (
        root / "results" / "benchmark" / problem_name / model / f"round_{round_number}"
    )


def read_generation_record(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid result record")
    return record


def generation_complete(record):
    if not isinstance(record, dict):
        return False
    call = record.get("call")
    if not isinstance(call, dict) or call.get("status") not in {"success", "error"}:
        return False
    if "record_complete" in record:
        return record["record_complete"] is True and (
            call["status"] == "error"
            or (
                isinstance(record.get("generation"), dict)
                and "extracted_code" in record
                and (
                    record["extracted_code"] is None
                    or isinstance(record["extracted_code"], str)
                )
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
        "AC",
        "WA",
        "TLE",
        "OLE",
        "RE",
        "NO_CODE",
    }


def validate_artifacts(folder: Path, record):
    """Check persisted files only; request identity and retry policy belong to runners."""
    if not generation_complete(record):
        raise ValueError("generation incomplete")
    # A failed provider response is still a received response, unlike a call exception.
    received = (
        record.get("generation") is not None or record["call"]["status"] == "success"
    )
    candidate = folder / "candidate.py"
    if received:
        raw = json.loads((folder / "response.json").read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("invalid response JSON object")
        generation = record.get("generation") or {}
        # Compare saved response metadata with its raw file, not the requested model/settings.
        # Legacy records without response metadata retain their original validation contract.
        if "response_id" in generation:
            fields = {
                "id": "response_id",
                "status": "status",
                "usage": "usage",
                "service_tier": "service_tier",
            }
            if any(
                raw.get(raw_key) != generation.get(saved_key)
                for raw_key, saved_key in fields.items()
            ):
                raise ValueError("raw response metadata differs from saved generation")
            if raw.get("model") != record.get("model", {}).get("response_model"):
                raise ValueError("raw response model differs from saved response model")
        code = record["extracted_code"]
        if code is not None:
            if not isinstance(code, str) or candidate.read_bytes() != code.encode(
                "utf-8"
            ):
                raise ValueError("후보 코드가 원본 extracted_code와 다름")
        elif candidate.exists():
            raise ValueError("unexpected candidate")
    elif candidate.exists() or (folder / "response.json").exists():
        raise ValueError("unexpected artifacts for a call without a response")
