"""Sealed evaluation preparation and append-only offline judging attempts."""

import difflib
import fcntl
import hashlib
import json
import math
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_eval.judging.engine import JUDGE_POLICY, judge_problem
from llm_eval.judging.workflow import CLOUD_MODELS, MODEL_IDS, digest
from llm_eval.shared.artifacts import generation_complete, generation_dir, validate_artifacts
from llm_eval.shared.problems import load_problems
from llm_eval.shared.storage import write_bytes, write_json, write_text
from llm_eval.shared.workloads import workload


SCHEMA_VERSION = 1
INFRASTRUCTURE_STATUSES = frozenset({"JUDGE_ERROR"})
REPAIR_EXCLUDED_STATUSES = frozenset({"AC", "CALL_ERROR", "NO_CODE", "JUDGE_ERROR"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_bytes(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}을 읽을 수 없습니다: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}은 JSON 객체여야 합니다: {path}")
    return value


def _safe_id(value: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or Path(value).name != value
        or "/" in value
        or "\\" in value
    ):
        raise ValueError(f"잘못된 {label}: {value!r}")
    return value


def _relative_file(base: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"잘못된 {label} 경로")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} 경로가 허용 범위를 벗어남: {relative}")
    base = base.resolve()
    path = (base / candidate).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise ValueError(f"{label} 파일을 찾을 수 없음: {relative}")
    return path


def _root_relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError as exc:
        raise ValueError(f"저장소 밖의 파일은 기록할 수 없습니다: {path}") from exc


def _test_files(root: Path, problem: dict) -> list[Path]:
    folder = _relative_directory(root, problem["problem_dir"], "문제 데이터")
    inputs = sorted(folder.glob(f"{problem['name']}.in.*"))
    if not inputs:
        raise ValueError(f"테스트 케이스 없음: {folder}")
    files = []
    for input_path in inputs:
        output_path = input_path.with_name(input_path.name.replace(".in.", ".out.", 1))
        if not output_path.is_file():
            raise ValueError(f"정답 파일 없음: {output_path}")
        files.extend((input_path, output_path))
    return files


def _relative_directory(base: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"잘못된 {label} 경로")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} 경로가 허용 범위를 벗어남: {relative}")
    base = base.resolve()
    path = (base / candidate).resolve()
    if not path.is_relative_to(base) or not path.is_dir():
        raise ValueError(f"{label} 디렉터리를 찾을 수 없음: {relative}")
    return path


def _policy(root: Path) -> tuple[Path, dict]:
    path = root / "configs/evaluation.json"
    policy = _read_json_object(path, "평가 정책")
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("지원하지 않는 평가 정책 schema_version")
    models = policy.get("models")
    rounds = policy.get("rounds")
    local_models = policy.get("local_models")
    if (
        not isinstance(models, list)
        or not models
        or len(models) != len(set(models))
        or models != list(MODEL_IDS)
        or not isinstance(local_models, list)
        or len(local_models) != len(set(local_models))
        or local_models != ["qwen36", "gemma4"]
        or not isinstance(rounds, list)
        or not rounds
        or len(rounds) != len(set(rounds))
        or any(isinstance(number, bool) or not isinstance(number, int) for number in rounds)
        or rounds != [1, 2]
    ):
        raise ValueError("평가 정책의 모델/회차 목록이 잘못되었습니다.")
    planned = policy.get("planned_attempts_per_model")
    minimum = policy.get("minimum_valid_originals")
    multiplier = policy.get("diagnostic_multiplier")
    if (
        isinstance(planned, bool)
        or not isinstance(planned, int)
        or planned <= 0
        or isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or minimum <= 0
        or minimum > planned
        or isinstance(multiplier, bool)
        or not isinstance(multiplier, (int, float))
        or not math.isfinite(multiplier)
        or multiplier <= 1
    ):
        raise ValueError("평가 정책의 횟수/배수 값이 잘못되었습니다.")
    return path, policy


def _baseline_result(root: Path, baseline: Path, item: dict) -> tuple[dict, Path | None]:
    if item.get("status") == "CALL_ERROR":
        if item.get("judge_path") is not None:
            raise ValueError("CALL_ERROR 항목에는 baseline judge가 없어야 합니다.")
        return {"status": "CALL_ERROR", "test_results": []}, None
    judge_path = _relative_file(baseline, item.get("judge_path"), "baseline judge")
    judge = _read_json_object(judge_path, "baseline judge")
    if judge.get("status") != item.get("status"):
        raise ValueError("baseline manifest와 judge 판정이 일치하지 않습니다.")
    if judge.get("source_run_id") != item.get("source_run_id"):
        raise ValueError("baseline judge의 source_run_id가 일치하지 않습니다.")
    return judge, judge_path


def _has_tle(judge: dict) -> bool:
    tests = judge.get("test_results", [])
    if not isinstance(tests, list):
        raise ValueError("baseline test_results가 목록이 아닙니다.")
    return any(
        isinstance(result, dict) and result.get("status") == "TLE" for result in tests
    )


def _add_source(root: Path, sources: dict[str, str], path: Path) -> None:
    relative = _root_relative(root, path)
    value = digest(path)
    previous = sources.setdefault(relative, value)
    if previous != value:
        raise ValueError(f"동일 경로의 해시가 달라졌습니다: {relative}")


def _entry_review_default(entry: dict, baseline_judge: dict) -> dict:
    return {
        "explanation": {"score": None, "evidence": ""},
        "repair": {
            "decision": None,
            "reason": "",
            "algorithm_preserved": None,
            "code_path": None,
        },
    }


def _validate_review(review: dict) -> None:
    explanation = review.get("explanation")
    repair = review.get("repair")
    if not isinstance(explanation, dict) or set(explanation) != {"score", "evidence"}:
        raise ValueError("review explanation 형식이 잘못되었습니다.")
    score = explanation["score"]
    evidence = explanation["evidence"]
    if (
        (score is not None and type(score) is not int)
        or score not in {None, 0, 1, 2}
        or not isinstance(evidence, str)
        or (score is not None and not evidence.strip())
    ):
        raise ValueError("review explanation 값이 잘못되었습니다.")
    required = {"decision", "reason", "algorithm_preserved", "code_path"}
    if not isinstance(repair, dict) or set(repair) != required:
        raise ValueError("review repair 형식이 잘못되었습니다.")
    if repair["decision"] not in {None, "not_applicable", "not_repairable", "candidate"}:
        raise ValueError("review repair decision이 잘못되었습니다.")
    algorithm_preserved = repair["algorithm_preserved"]
    if not isinstance(repair["reason"], str) or (
        algorithm_preserved is not None and type(algorithm_preserved) is not bool
    ):
        raise ValueError("review repair 값이 잘못되었습니다.")
    if repair["code_path"] is not None and not isinstance(repair["code_path"], str):
        raise ValueError("review code_path가 잘못되었습니다.")


def prepare_evaluation(root: Path, baseline_id: str) -> Path:
    root = Path(root).resolve()
    baseline_id = _safe_id(baseline_id, "baseline ID")
    policy_path, policy = _policy(root)
    baseline = root / "results/judging" / baseline_id
    baseline_manifest_path = baseline / "manifest.json"
    baseline_manifest = _read_json_object(baseline_manifest_path, "baseline manifest")
    if (
        baseline_manifest.get("complete") is not True
        or baseline_manifest.get("session_id") != baseline_id
    ):
        raise ValueError("완료된 baseline 채점 세션만 평가할 수 있습니다.")
    if policy["planned_attempts_per_model"] != len(load_problems(root)) * len(
        policy["rounds"]
    ):
        raise ValueError("planned_attempts_per_model이 문제 수와 회차 수에 맞지 않습니다.")

    judging_source = root / "src/llm_eval/judging"
    engine_path = judging_source / "engine.py"
    execution_path = judging_source / "execution.py"
    workflow_path = judging_source / "workflow.py"
    if baseline_manifest.get("judge_sha256") != digest(engine_path) or baseline_manifest.get(
        "judge_process_sha256"
    ) != digest(execution_path) or baseline_manifest.get("judge_policy") != JUDGE_POLICY:
        raise ValueError("baseline 채점 구현이 현재 engine/execution과 다릅니다.")

    problems = load_problems(root)
    if not isinstance(problems, list) or not problems:
        raise ValueError("문제 메타데이터가 비어 있습니다.")
    by_id = {item.get("id"): item for item in problems if isinstance(item, dict)}
    if len(by_id) != len(problems):
        raise ValueError("문제 ID가 없거나 중복되었습니다.")
    sources: dict[str, str] = {}
    for path in (
        root / "data/coci/problems.json",
        baseline_manifest_path,
        engine_path,
        execution_path,
        workflow_path,
    ):
        _add_source(root, sources, path)

    overrides = policy.get("effective_limit_overrides")
    if not isinstance(overrides, dict):
        raise ValueError("effective_limit_overrides가 객체가 아닙니다.")
    for problem_id, override in overrides.items():
        problem = by_id.get(problem_id)
        if problem is None or not isinstance(override, dict):
            raise ValueError(f"알 수 없는 제한시간 override: {problem_id}")
        if set(override) != {"official_seconds", "effective_seconds"}:
            raise ValueError(f"잘못된 제한시간 override: {problem_id}")
        if override["official_seconds"] != problem.get("time_limit_seconds"):
            raise ValueError(f"공식 제한시간 override 불일치: {problem_id}")
        if override["effective_seconds"] != override["official_seconds"] * policy[
            "diagnostic_multiplier"
        ]:
            raise ValueError(f"유효 제한시간 배수 불일치: {problem_id}")
    for problem in problems:
        statement = _relative_file(root, problem.get("statement_path"), "문제문")
        _relative_directory(root, problem.get("problem_dir"), "문제 데이터")
        _add_source(root, sources, statement)

    entries = []
    seen = set()
    baseline_entries = baseline_manifest.get("entries")
    if not isinstance(baseline_entries, list):
        raise ValueError("baseline entries가 목록이 아닙니다.")
    for item in baseline_entries:
        if not isinstance(item, dict):
            raise ValueError("baseline entry가 객체가 아닙니다.")
        problem = by_id.get(item.get("problem_id"))
        model = item.get("model")
        number = item.get("round")
        if (
            problem is None
            or item.get("problem_name") != problem.get("name")
            or model not in policy["models"]
            or number not in policy["rounds"]
        ):
            raise ValueError("baseline 항목의 문제/모델/회차가 정책과 일치하지 않습니다.")
        key = f"{problem['name']}/{model}/round_{number}"
        if key in seen:
            raise ValueError(f"중복 baseline 항목: {key}")
        seen.add(key)
        official = problem.get("time_limit_seconds")
        if (
            isinstance(official, bool)
            or not isinstance(official, (int, float))
            or not math.isfinite(official)
            or official <= 0
            or item.get("time_limit_seconds") != official
        ):
            raise ValueError(f"공식 제한시간 불일치: {key}")

        source_result = _relative_file(root, item.get("source_result"), "원본 result")
        expected_source = generation_dir(root, problem["name"], model, number) / "result.json"
        if source_result != expected_source.resolve():
            raise ValueError(f"원본 result 경로가 표준 생성 경로가 아닙니다: {key}")
        record = _read_json_object(source_result, "원본 result")
        expected_type = "cloud" if model in CLOUD_MODELS else "benchmark"
        if (
            not generation_complete(record)
            or record.get("run_id") != item.get("source_run_id")
            or record.get("problem", {}).get("id") != problem["id"]
            or record.get("problem", {}).get("time_limit_seconds") != official
            or record.get("model", {}).get("id") != MODEL_IDS[model]
            or record.get("experiment", {}).get("round") != number
            or record.get("experiment", {}).get("type") != expected_type
        ):
            raise ValueError(f"원본 생성 기록 신원 불일치: {key}")
        source_folder = source_result.parent
        validate_artifacts(source_folder, record)
        if item.get("source_sha256") != digest(source_result):
            raise ValueError(f"baseline source hash 불일치: {key}")
        call_error = record["call"]["status"] == "error"
        if (item.get("status") == "CALL_ERROR") != call_error:
            raise ValueError(f"baseline CALL_ERROR 상태 불일치: {key}")
        has_code = not call_error and record.get("extracted_code") is not None
        if (item.get("candidate_path") is not None) != has_code:
            raise ValueError(f"baseline candidate 존재 여부 불일치: {key}")
        _add_source(root, sources, source_result)
        response_path = source_folder / "response.json"
        if response_path.is_file():
            _add_source(root, sources, response_path)

        candidate_path = None
        if item.get("candidate_path") is not None:
            candidate = _relative_file(root, item["candidate_path"], "원본 candidate")
            if candidate != (source_folder / "candidate.py").resolve():
                raise ValueError(f"원본 candidate 경로가 생성 기록과 다릅니다: {key}")
            if item.get("candidate_sha256") != digest(candidate):
                raise ValueError(f"baseline candidate hash 불일치: {key}")
            candidate_path = _root_relative(root, candidate)
            _add_source(root, sources, candidate)
        judge, judge_path = _baseline_result(root, baseline, item)
        if judge_path is not None and judge.get("time_limit_seconds") != official:
            raise ValueError(f"baseline judge 공식 제한시간 불일치: {key}")
        if judge_path is not None and (
            judge.get("source_result") != item["source_result"]
            or judge.get("source_sha256") != item["source_sha256"]
            or judge.get("candidate_sha256") != item.get("candidate_sha256")
        ):
            raise ValueError(f"baseline judge source/candidate 신원 불일치: {key}")
        if judge_path is not None:
            _add_source(root, sources, judge_path)
        for test_path in _test_files(root, problem):
            _add_source(root, sources, test_path)
        test_identity = baseline_manifest.get("test_data", {}).get(problem["id"], [])
        expected_tests = {
            source["path"]: source["sha256"]
            for source in test_identity
            if isinstance(source, dict) and set(source) >= {"path", "sha256"}
        }
        for test_path in _test_files(root, problem):
            relative = _root_relative(root, test_path)
            if candidate_path is not None and expected_tests.get(relative) != digest(test_path):
                raise ValueError(f"baseline 테스트 데이터 신원 불일치: {key}")

        override = overrides.get(problem["id"])
        effective = override["effective_seconds"] if override is not None else official
        diagnostic = official * policy["diagnostic_multiplier"]
        entries.append(
            {
                "key": key,
                "problem_id": problem["id"],
                "problem_name": problem["name"],
                "model": model,
                "round": number,
                "source_result": _root_relative(root, source_result),
                "source_run_id": item["source_run_id"],
                "candidate_path": candidate_path,
                "baseline_judge": _root_relative(root, judge_path) if judge_path else None,
                "official_limit_seconds": official,
                "effective_limit_seconds": effective,
                "diagnostic_limit_seconds": diagnostic,
                "needs_limit_run": _has_tle(judge),
                "limit_role": "scoring" if override is not None else "diagnostic",
            }
        )

    expected = {
        f"{problem['name']}/{model}/round_{number}"
        for problem in problems
        for model in policy["models"]
        for number in policy["rounds"]
    }
    unknown = seen - expected
    if unknown:
        raise ValueError(f"정책 밖 baseline 항목: {sorted(unknown)}")
    missing = sorted(expected - seen)
    evaluation_id = (
        datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ") + "_" + uuid4().hex[:8]
    )
    folder = root / "results/evaluation" / evaluation_id
    folder.mkdir(parents=True, exist_ok=False)
    policy_target = folder / "policy.json"
    write_bytes(policy_target, policy_path.read_bytes())
    policy_sha256 = digest(policy_target)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "created_at": _now(),
        "baseline": {
            "id": baseline_id,
            "path": _root_relative(root, baseline),
            "manifest": _root_relative(root, baseline_manifest_path),
            "manifest_sha256": digest(baseline_manifest_path),
        },
        "policy": policy,
        "policy_sha256": policy_sha256,
        "policy_source": {
            "path": _root_relative(root, policy_path),
            "sha256_at_prepare": digest(policy_path),
        },
        "judge_policy": dict(JUDGE_POLICY),
        "problems": problems,
        "entries": entries,
        "sources": [
            {"path": path, "sha256": value} for path, value in sorted(sources.items())
        ],
        "missing": missing,
    }
    write_json(folder / "manifest.json", manifest)
    write_text(folder / "manifest.seal", digest(folder / "manifest.json") + "\n")
    for entry in entries:
        if entry["baseline_judge"] is None:
            baseline_judge = {"status": "CALL_ERROR", "test_results": []}
        else:
            baseline_judge = _read_json_object(root / entry["baseline_judge"], "baseline judge")
        review_path = folder / "reviews" / entry["key"] / "review.json"
        review_path.parent.mkdir(parents=True, exist_ok=False)
        write_json(review_path, _entry_review_default(entry, baseline_judge))
    return folder


def _validate_attempt(folder: Path, entry_keys: set[str], attempt_path: Path) -> dict:
    attempt = _read_json_object(attempt_path, "평가 attempt")
    if attempt.get("entry_key") not in entry_keys or attempt.get("kind") not in {
        "limits",
        "repairs",
    }:
        raise ValueError(f"attempt 신원이 잘못되었습니다: {attempt_path}")
    if attempt.get("attempt_id") != attempt_path.parent.name:
        raise ValueError(f"attempt ID가 경로와 다릅니다: {attempt_path}")
    status = attempt.get("status")
    if status not in {"completed", "error", "interrupted", "running"}:
        raise ValueError(f"attempt 상태가 잘못되었습니다: {attempt_path}")
    terminal = status in {"completed", "error", "interrupted"}
    seal_path = attempt_path.with_name("attempt.seal")
    if terminal:
        try:
            seal = seal_path.read_text(encoding="ascii").strip()
        except OSError as exc:
            raise ValueError(f"terminal attempt seal이 없습니다: {attempt_path}") from exc
        if seal != digest(attempt_path):
            raise ValueError(f"terminal attempt가 봉인 이후 변경되었습니다: {attempt_path}")
    elif seal_path.exists():
        raise ValueError(f"running attempt에 terminal seal이 있습니다: {attempt_path}")
    input_data = attempt.get("input")
    if not isinstance(input_data, dict) or attempt.get("input_sha256") != _sha256_bytes(
        _json_bytes(input_data)
    ):
        raise ValueError(f"attempt input metadata가 일치하지 않습니다: {attempt_path}")
    for path_key, hash_key in (
        ("code_snapshot", "code_snapshot_sha256"),
        ("diff_path", "diff_sha256"),
    ):
        artifact = _relative_file(folder, attempt.get(path_key), "attempt artifact")
        if digest(artifact) != attempt.get(hash_key):
            raise ValueError(f"attempt artifact가 변경되었습니다: {artifact}")
    if attempt.get("candidate_sha256") != attempt.get("code_snapshot_sha256"):
        raise ValueError(f"attempt candidate hash가 snapshot과 다릅니다: {attempt_path}")
    if input_data.get("kind") != attempt.get("kind") or input_data.get(
        "candidate_sha256"
    ) != attempt.get("candidate_sha256") or input_data.get("limit") != attempt.get(
        "effective_limit_seconds"
    ):
        raise ValueError(f"attempt input metadata 값이 다릅니다: {attempt_path}")
    if attempt.get("judge_policy") != JUDGE_POLICY:
        raise ValueError(f"attempt judge policy가 현재 정책과 다릅니다: {attempt_path}")
    if status == "completed":
        result = attempt.get("result")
        if not isinstance(result, dict) or result.get("status") in INFRASTRUCTURE_STATUSES:
            raise ValueError(f"완료 attempt의 result가 잘못되었습니다: {attempt_path}")
        for source in attempt.get("implementation", []):
            if not isinstance(source, dict):
                raise ValueError("attempt implementation 형식이 잘못되었습니다.")
            path = _relative_file(folder.parent.parent.parent, source.get("path"), "구현 source")
            if digest(path) != source.get("sha256"):
                raise ValueError(f"완료 attempt 구현이 변경되었습니다: {path}")
    attempt["_path"] = str(attempt_path.relative_to(folder))
    return attempt


def load_evaluation(root: Path, evaluation_id: str) -> tuple[Path, dict]:
    root = Path(root).resolve()
    evaluation_id = _safe_id(evaluation_id, "evaluation ID")
    folder = root / "results/evaluation" / evaluation_id
    manifest_path = folder / "manifest.json"
    seal_path = folder / "manifest.seal"
    manifest = _read_json_object(manifest_path, "평가 manifest")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get(
        "evaluation_id"
    ) != evaluation_id:
        raise ValueError("평가 manifest 신원이 일치하지 않습니다.")
    try:
        seal = seal_path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise ValueError("평가 manifest seal을 읽을 수 없습니다.") from exc
    if seal != digest(manifest_path):
        raise ValueError("평가 manifest가 봉인 이후 변경되었습니다.")
    policy_path = _relative_file(folder, "policy.json", "평가 policy")
    if digest(policy_path) != manifest.get("policy_sha256"):
        raise ValueError("평가 policy 복사본이 변경되었습니다.")
    if _read_json_object(policy_path, "평가 policy") != manifest.get("policy"):
        raise ValueError("평가 policy와 manifest snapshot이 다릅니다.")
    for source in manifest.get("sources", []):
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            raise ValueError("평가 source 형식이 잘못되었습니다.")
        path = _relative_file(root, source["path"], "평가 source")
        if digest(path) != source["sha256"]:
            raise ValueError(f"평가 준비 이후 source가 변경되었습니다: {source['path']}")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError("평가 entries가 잘못되었습니다.")
    keys = [entry.get("key") for entry in entries]
    if any(not isinstance(key, str) for key in keys) or len(keys) != len(set(keys)):
        raise ValueError("평가 entry key가 없거나 중복되었습니다.")
    for attempt_path in sorted((folder / "attempts").glob("**/attempt.json")):
        _validate_attempt(folder, set(keys), attempt_path)
    return folder, manifest


def read_entry(root: Path, folder: Path, manifest: dict, entry: dict) -> dict:
    root = Path(root).resolve()
    folder = Path(folder).resolve()
    if entry not in manifest.get("entries", []):
        raise ValueError("manifest에 없는 entry입니다.")
    record = _read_json_object(_relative_file(root, entry["source_result"], "원본 result"), "원본 result")
    if record.get("run_id") != entry["source_run_id"]:
        raise ValueError("원본 result의 run_id가 entry와 다릅니다.")
    if entry["baseline_judge"] is None:
        baseline = {"status": "CALL_ERROR", "test_results": []}
    else:
        baseline = _read_json_object(
            _relative_file(root, entry["baseline_judge"], "baseline judge"),
            "baseline judge",
        )
    review_path = folder / "reviews" / entry["key"] / "review.json"
    review = _read_json_object(review_path, "평가 review")
    _validate_review(review)
    current_repair_sha256 = None
    repair = review["repair"]
    if repair["decision"] == "candidate" and repair["code_path"] is not None:
        relative = Path(repair["code_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("수정 candidate 경로가 저장소 범위를 벗어났습니다.")
        repair_path = (root / relative).resolve()
        if not repair_path.is_relative_to(root):
            raise ValueError("수정 candidate 경로가 저장소 범위를 벗어났습니다.")
        if repair_path.is_file() and entry["candidate_path"] != _root_relative(root, repair_path):
            current_repair_sha256 = digest(repair_path)
    attempt_paths = sorted((folder / "attempts" / entry["key"]).glob("*/attempt.json"))
    attempts = [_validate_attempt(folder, {entry["key"]}, path) for path in attempt_paths]
    return {
        "record": record,
        "baseline": baseline,
        "review": review,
        "attempts": attempts,
        "current_repair_sha256": current_repair_sha256,
    }


@contextmanager
def _evaluation_lock(folder: Path):
    with (folder / ".lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("다른 평가 실행이 진행 중입니다.") from exc
        yield


def _implementation(root: Path) -> list[dict]:
    judging_source = root / "src/llm_eval/judging"
    return [
        {"path": _root_relative(root, path), "sha256": digest(path)}
        for path in (
            judging_source / "engine.py",
            judging_source / "execution.py",
            judging_source / "workflow.py",
            judging_source / "evaluation.py",
        )
    ]


def _new_attempt(
    root: Path,
    folder: Path,
    entry: dict,
    kind: str,
    code: bytes,
    original: bytes,
    limit: float,
    review: dict,
    input_data: dict,
) -> tuple[Path, dict]:
    attempt_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ") + "_" + uuid4().hex[:8]
    attempt_folder = folder / "attempts" / entry["key"] / attempt_id
    attempt_folder.mkdir(parents=True, exist_ok=False)
    code_path = attempt_folder / "candidate.py"
    diff_path = attempt_folder / "candidate.diff"
    write_bytes(code_path, code)
    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            code.decode("utf-8").splitlines(keepends=True),
            fromfile="original/candidate.py",
            tofile="attempt/candidate.py",
        )
    ).encode("utf-8")
    write_bytes(diff_path, diff)
    attempt = {
        "attempt_id": attempt_id,
        "entry_key": entry["key"],
        "kind": kind,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
        "result": None,
        "effective_limit_seconds": limit,
        "candidate_sha256": _sha256_bytes(code),
        "review": review,
        "input": input_data,
        "input_sha256": _sha256_bytes(_json_bytes(input_data)),
        "code_snapshot": str(code_path.relative_to(folder)),
        "code_snapshot_sha256": digest(code_path),
        "diff_path": str(diff_path.relative_to(folder)),
        "diff_sha256": digest(diff_path),
        "implementation": _implementation(root),
        "judge_policy": dict(JUDGE_POLICY),
        "error": None,
    }
    write_json(attempt_folder / "attempt.json", attempt)
    return attempt_folder, attempt


def _finish_attempt(path: Path, attempt: dict, status: str, result=None, error=None) -> None:
    attempt["status"] = status
    attempt["finished_at"] = _now()
    attempt["result"] = result
    attempt["error"] = error
    attempt_path = path / "attempt.json"
    write_json(attempt_path, attempt)
    write_text(path / "attempt.seal", digest(attempt_path) + "\n")


def _matching_completed(state: dict, kind: str, input_sha256: str) -> bool:
    return any(
        attempt.get("kind") == kind
        and attempt.get("status") == "completed"
        and attempt.get("input_sha256") == input_sha256
        for attempt in state["attempts"]
    )


def run_evaluation(root: Path, evaluation_id: str, kind: str) -> Path:
    if kind not in {"limits", "repairs"}:
        raise ValueError(f"지원하지 않는 평가 실행 종류: {kind}")
    root = Path(root).resolve()
    folder, _manifest = load_evaluation(root, evaluation_id)
    with workload(root, "judge"), _evaluation_lock(folder):
        folder, manifest = load_evaluation(root, evaluation_id)
        problems = {problem["id"]: problem for problem in manifest["problems"]}
        for entry in manifest["entries"]:
            state = read_entry(root, folder, manifest, entry)
            original_path = (
                _relative_file(root, entry["candidate_path"], "원본 candidate")
                if entry["candidate_path"] is not None
                else None
            )
            if original_path is None:
                continue
            original = original_path.read_bytes()
            if kind == "limits":
                if not entry["needs_limit_run"]:
                    continue
                code = original
                review = state["review"]
                limit = (
                    entry["effective_limit_seconds"]
                    if entry["limit_role"] == "scoring"
                    else entry["diagnostic_limit_seconds"]
                )
                input_data = {
                    "kind": kind,
                    "candidate_sha256": _sha256_bytes(code),
                    "limit": limit,
                }
            else:
                repair = state["review"]["repair"]
                verdict, source = project_verdict(entry, state)
                if (
                    state["baseline"].get("status") in REPAIR_EXCLUDED_STATUSES
                    or verdict is None
                    or verdict.get("status") in REPAIR_EXCLUDED_STATUSES
                ):
                    continue
                if repair["decision"] != "candidate":
                    continue
                if repair["algorithm_preserved"] is not True or repair["code_path"] is None:
                    raise ValueError(f"수정 후보 검토가 미완성입니다: {entry['key']}")
                if not repair["reason"].strip():
                    raise ValueError(f"수정 사유가 비어 있습니다: {entry['key']}")
                code_path = _relative_file(root, repair["code_path"], "수정 candidate")
                if _root_relative(root, code_path) == entry["candidate_path"]:
                    raise ValueError(f"원본 candidate를 수정본으로 사용할 수 없습니다: {entry['key']}")
                code = code_path.read_bytes()
                if code == original:
                    raise ValueError(f"수정 candidate가 원본과 동일합니다: {entry['key']}")
                review = state["review"]
                limit = (
                    entry["effective_limit_seconds"]
                    if entry["limit_role"] == "scoring"
                    else entry["official_limit_seconds"]
                )
                input_data = {
                    "kind": kind,
                    "candidate_sha256": _sha256_bytes(code),
                    "repair": review["repair"],
                    "project_verdict": verdict,
                    "project_verdict_source": source,
                    "limit": limit,
                }
            input_sha256 = _sha256_bytes(_json_bytes(input_data))
            if _matching_completed(state, kind, input_sha256):
                continue
            attempt_folder, attempt = _new_attempt(
                root,
                folder,
                entry,
                kind,
                code,
                original,
                limit,
                review,
                input_data,
            )
            try:
                _validate_attempt(
                    folder, {entry["key"]}, attempt_folder / "attempt.json"
                )
                problem = problems[entry["problem_id"]]
                result = judge_problem(
                    code_path=attempt_folder / "candidate.py",
                    problem_dir=_relative_directory(root, problem["problem_dir"], "문제 데이터"),
                    problem_name=entry["problem_name"],
                    time_limit_seconds=limit,
                )
                load_evaluation(root, evaluation_id)
                if not isinstance(result, dict) or result.get("status") in INFRASTRUCTURE_STATUSES:
                    _finish_attempt(
                        attempt_folder,
                        attempt,
                        "error",
                        result=result if isinstance(result, dict) else None,
                        error={"type": "JudgeInfrastructureError"},
                    )
                    raise RuntimeError(f"평가 채점 인프라 오류: {entry['key']}")
                _finish_attempt(attempt_folder, attempt, "completed", result=result)
            except BaseException as exc:
                if attempt.get("status") == "running":
                    status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
                    _finish_attempt(
                        attempt_folder,
                        attempt,
                        status,
                        error={"type": type(exc).__name__},
                    )
                raise
    return folder


def project_verdict(entry: dict, state: dict) -> tuple[dict | None, str]:
    """Return the result used by project scoring and its provenance label."""
    if entry["limit_role"] == "scoring" and entry["needs_limit_run"]:
        completed = [
            attempt
            for attempt in state.get("attempts", [])
            if attempt.get("kind") == "limits"
            and attempt.get("status") == "completed"
            and isinstance(attempt.get("result"), dict)
            and attempt["result"].get("status") != "JUDGE_ERROR"
        ]
        if not completed:
            return None, "pending_limits"
        return completed[-1]["result"], "limit_2x"
    return state["baseline"], "baseline_1x"
