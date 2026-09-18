import json
from pathlib import Path

# Compared field by field against the raw response file. A chat completion carries
# neither a status nor a service tier, so those are absent rather than mismatched.
RESPONSE_FIELDS = {
    "openai_responses": {
        "id": "response_id",
        "status": "status",
        "usage": "usage",
        "service_tier": "service_tier",
    },
    "openai_chat_completions": {"id": "response_id", "usage": "usage"},
}


def generation_dir(
    root: Path, problem_name: str, model: str, round_number: int | None
) -> Path:
    if round_number is None:
        return root / "results" / "demo" / problem_name / model
    return (
        root / "results" / "benchmark" / problem_name / model / f"round_{round_number}"
    )


def reset_demo_dir(root: Path, problem_name: str, model: str) -> Path:
    """Reset only generated files in one demo target without following symlinked paths."""
    demo_root = root / "results" / "demo"
    folder = demo_root / problem_name / model
    try:
        relative = folder.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"demo 경로가 저장소 밖을 가리킵니다: {folder}") from exc

    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"demo 경로의 심볼릭 링크는 초기화할 수 없습니다: {current}"
            )

    benchmark_root = (root / "results" / "benchmark").resolve()
    resolved_demo_root = demo_root.resolve()
    resolved = folder.resolve()
    if resolved != resolved_demo_root and resolved_demo_root not in resolved.parents:
        raise ValueError(f"demo 경로가 demo 폴더 밖을 가리킵니다: {folder}")
    if resolved == benchmark_root or benchmark_root in resolved.parents:
        raise ValueError(f"demo 경로가 benchmark를 가리킵니다: {folder}")

    folder.mkdir(parents=True, exist_ok=True)
    for name in ("result.json", "response.json", "candidate.py"):
        (folder / name).unlink(missing_ok=True)
    return folder


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
            # Legacy records carry no runtime and keep the Responses contract.
            runtime = record.get("model", {}).get("runtime")
            fields = RESPONSE_FIELDS.get(runtime, RESPONSE_FIELDS["openai_responses"])
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
