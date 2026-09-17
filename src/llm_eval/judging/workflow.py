"""Sequential, offline judging of immutable benchmark generation records."""

import fcntl
import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_eval.judging.engine import JUDGE_POLICY, judge_problem
from llm_eval.shared.problems import get_problem, load_problems
from llm_eval.shared.artifacts import generation_dir
from llm_eval.shared.storage import write_json
from llm_eval.shared.artifacts import generation_complete, validate_artifacts
from llm_eval.shared.workloads import workload, active_workloads

# Append new models; this order is the canonical model order of every judging session.
MODEL_IDS = {"qwen36": "qwen36", "gemma4": "gemma4", "luna": "gpt-5.6-luna",
             "motif3": "motif/motif-3"}
CLOUD_MODELS = frozenset({"luna", "motif3"})


def now():
    return datetime.now(UTC).isoformat()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_idle():
    found = active_workloads()
    if found:
        raise RuntimeError(f"생성기/모델 서버 실행 중: {found}. 종료 후 채점하세요.")


def choose(value, available, label):
    if value == "all":
        return list(available)
    values = value.split(",")
    if (not values or len(values) != len(set(values))
            or any(item not in available for item in values)):
        raise ValueError(f"잘못된 {label}: {value}; all 또는 {list(available)}")
    # Canonical order, independent of command-line ordering.
    return [item for item in available if item in values]


def test_identity(root, problem):
    folder = root / problem["problem_dir"]
    inputs = sorted(folder.glob(f"{problem['name']}.in.*"))
    if not inputs:
        raise ValueError(f"테스트 케이스 없음: {folder}")
    files = []
    for input_path in inputs:
        output = input_path.with_name(input_path.name.replace(".in.", ".out.", 1))
        for path in (input_path, output):
            files.append({"path": str(path.relative_to(root)), "sha256": digest(path)})
    return files


def collect(root, problems, models, rounds):
    entries, missing, datasets = [], [], {}
    for problem in problems:
        for model in models:
            for number in rounds:
                relative = generation_dir(root, problem["name"], model, number).relative_to(root)
                folder = root / relative
                if not folder.exists():
                    missing.append(str(relative))
                    continue
                path = folder / "result.json"
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                    expected_type = "cloud" if model in CLOUD_MODELS else "benchmark"
                    if (not generation_complete(record)
                            or record["problem"]["id"] != problem["id"]
                            or record["model"]["id"] != MODEL_IDS[model]
                            or record["experiment"]["round"] != int(number)
                            or record["experiment"]["type"] != expected_type
                            or not isinstance(record.get("run_id"), str)
                            or not record["run_id"]):
                        raise ValueError("생성 미완료 또는 원본 식별 정보 불일치")
                    limit = problem["time_limit_seconds"]
                    if (isinstance(limit, bool) or not isinstance(limit, (int, float))
                            or not math.isfinite(limit) or limit <= 0
                            or record["problem"]["time_limit_seconds"] != limit
                            or problem["judge_type"] != "token"):
                        raise ValueError("시간 제한/채점 정책 불일치")
                    code = record["extracted_code"]
                    candidate = folder / "candidate.py"
                    failed = record["call"]["status"] == "error"
                    validate_artifacts(folder, record)
                    if not failed and code is not None and problem["id"] not in datasets:
                        datasets[problem["id"]] = test_identity(root, problem)
                    entry = {
                        "problem_id": problem["id"], "problem_name": problem["name"],
                        "model": model, "model_id": record["model"]["id"], "round": int(number),
                        "source_run_id": record["run_id"], "source_result": str(relative / "result.json"),
                        "source_sha256": digest(path),
                        "candidate_path": str(relative / "candidate.py") if not failed and code is not None else None,
                        "candidate_sha256": digest(candidate) if not failed and code is not None else None,
                        "time_limit_seconds": limit, "judge_type": "token",
                        "status": "CALL_ERROR" if failed else "pending",
                        "judge_path": None,
                    }
                    entries.append(entry)
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    raise ValueError(f"불완전하거나 일치하지 않는 결과: {path} ({exc})") from exc
    return entries, missing, datasets


def verify_sources(root, entry, test_files):
    if digest(root / entry["source_result"]) != entry["source_sha256"]:
        raise ValueError("채점 준비 이후 생성 기록 변경")
    if entry["candidate_path"] and digest(root / entry["candidate_path"]) != entry["candidate_sha256"]:
        raise ValueError("채점 준비 이후 후보 코드 변경")
    for item in test_files:
        if digest(root / item["path"]) != item["sha256"]:
            raise ValueError("채점 준비 이후 테스트 데이터 변경")


def _run_batch(root, problem_selection="all", model_selection="all", round_selection="all"):
    root = root.resolve()
    available = load_problems(root)
    ids = choose(problem_selection, [p["id"] for p in available], "문제 ID")
    models = choose(model_selection, MODEL_IDS, "모델")
    rounds = choose(round_selection, ["1", "2"], "회차")
    problems = [p for p in available if p["id"] in ids]
    require_idle()
    output_root = root / "results/judging"
    output_root.mkdir(parents=True, exist_ok=True)
    # Prevent simultaneous judges for this checkout; never remove a held lock file.
    with (output_root / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("다른 일괄 채점이 실행 중입니다.") from exc
        entries, missing, datasets = collect(root, problems, models, rounds)
        for path in missing:
            print(f"미생성: {path}")
        if not entries:
            raise ValueError("선택 범위에 저장 완료된 생성 기록이 없습니다.")
        session_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ") + "_" + uuid4().hex[:8]
        session = output_root / session_id
        session.mkdir(exist_ok=False)
        manifest = build_manifest(session_id, ids, models, rounds, missing, datasets, entries)
        manifest_path = session / "manifest.json"
        write_json(manifest_path, manifest)
        print(f"채점 세션: {session}")
        current = None
        try:
            for entry in entries:
                current = entry
                require_idle()
                if entry["status"] == "CALL_ERROR":
                    continue
                process_entry(root, session, session_id, entry, problems, datasets)
                write_json(manifest_path, manifest)
            manifest["complete"] = True
            manifest["status"] = "completed_with_missing" if missing else "completed"
        except BaseException as exc:
            manifest["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "error"
            manifest["error"] = {"type": type(exc).__name__}
            if current is not None and current["status"] == "pending":
                current["status"] = "JUDGE_ERROR"
            raise
        finally:
            finish_manifest(manifest_path, manifest)
        return session


def run_batch_judging(root, problems="all", models="all", rounds="all"):
    with workload(root, "judge"):
        return _run_batch(root, problems, models, rounds)


def run_candidate_check(root, code_path, problem_id):
    with workload(root, "judge"):
        problem = get_problem(load_problems(root), problem_id)
        code_path = Path(code_path).resolve()
        if not code_path.is_file():
            raise ValueError(f"코드 파일을 찾을 수 없습니다: {code_path}")
        if problem["judge_type"] != "token":
            raise ValueError("현재는 token 방식의 문제만 지원합니다.")
        result = judge_problem(
            code_path=code_path, problem_dir=root / problem["problem_dir"],
            problem_name=problem["name"],
            time_limit_seconds=problem["time_limit_seconds"],
        )
    print("최종 판정:", result["status"])
    print("통과:", result["passed_cases"], "/", result["total_cases"])
    print("최대 실행 시간:", result["max_case_seconds"])
    return result


def build_manifest(session_id, ids, models, rounds, missing, datasets, entries):
    return {
        "session_id": session_id, "started_at": now(), "finished_at": None,
        "complete": False, "status": "running",
        "selection": {"problems": ids, "models": models, "rounds": [int(n) for n in rounds]},
        "timing": "wall_clock_subprocess_timeout_per_test",
        "python": sys.version, "python_executable": sys.executable,
        "platform": platform.platform(),
        "judge_sha256": digest(Path(__file__).with_name("engine.py")),
        "judge_process_sha256": digest(Path(__file__).with_name("execution.py")),
        "judge_policy": dict(JUDGE_POLICY),
        "missing": missing, "coverage_complete": not missing,
        "test_data": datasets, "entries": entries,
    }


def process_entry(root, session, session_id, entry, problems, datasets):
    problem = next(p for p in problems if p["id"] == entry["problem_id"])
    files = datasets.get(problem["id"], []) if entry["candidate_path"] else []
    verify_sources(root, entry, files)
    if entry["candidate_path"]:
        result = judge_problem(
            code_path=root / entry["candidate_path"],
            problem_dir=root / problem["problem_dir"], problem_name=problem["name"],
            time_limit_seconds=entry["time_limit_seconds"],
        )
    else:
        result = {"status": "NO_CODE", "passed_cases": 0, "total_cases": None,
                  "max_case_seconds": None, "time_limit_seconds": entry["time_limit_seconds"],
                  "test_results": []}
    verify_sources(root, entry, files)
    relative = Path(entry["problem_name"]) / entry["model"] / f"round_{entry['round']}" / "judge.json"
    target = session / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, {**result, "session_id": session_id, "judged_at": now(),
                        "source_run_id": entry["source_run_id"],
                        "source_result": entry["source_result"],
                        "source_sha256": entry["source_sha256"],
                        "candidate_sha256": entry["candidate_sha256"]})
    entry["status"] = result["status"]
    entry["judge_path"] = str(relative)

def finish_manifest(path, manifest):
    manifest["finished_at"] = now()
    write_json(path, manifest)
