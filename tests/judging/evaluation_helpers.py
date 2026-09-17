import json
from pathlib import Path

from llm_eval.judging import evaluation
from llm_eval.judging.engine import JUDGE_POLICY
from llm_eval.judging.workflow import digest
from llm_eval.shared.storage import write_json


def build_evaluation_fixture(
    root: Path, *, status="TLE", call_error=False, test_statuses=None
):
    source_judging = Path(evaluation.__file__).parent
    fixture_judging = root / "src/llm_eval/judging"
    fixture_judging.mkdir(parents=True)
    for name in ("engine.py", "execution.py", "workflow.py", "evaluation.py"):
        (fixture_judging / name).write_bytes((source_judging / name).read_bytes())
    problem = {
        "id": "id_a",
        "name": "a",
        "problem_dir": "data/a",
        "statement_path": "data/a/a.md",
        "time_limit_seconds": 1,
        "memory_limit_mib": 64,
        "judge_type": "token",
        "title": "A",
        "season": "fixture",
        "contest": "fixture",
        "difficulty": 1,
        "difficulty_reason": "fixture",
    }
    data = root / "data/a"
    data.mkdir(parents=True)
    (data / "a.md").write_text("fixture", encoding="utf-8")
    test_statuses = test_statuses or (["TLE"] if status == "TLE" else [status])
    for number in range(1, len(test_statuses) + 1):
        (data / f"a.in.{number}").write_text("1\n", encoding="utf-8")
        (data / f"a.out.{number}").write_text("1\n", encoding="utf-8")
    (root / "data/coci").mkdir(parents=True)
    write_json(root / "data/coci/problems.json", [problem])
    (root / "configs").mkdir()
    write_json(
        root / "configs/evaluation.json",
        {
            "schema_version": 1,
            "decision_phase": "during_generation",
            "preregistered": False,
            "planned_attempts_per_model": 2,
            "minimum_valid_originals": 1,
            "local_models": ["qwen36", "gemma4"],
            "models": ["qwen36", "gemma4", "luna", "motif3"],
            "rounds": [1, 2],
            "diagnostic_multiplier": 2,
            "effective_limit_overrides": {
                "id_a": {"official_seconds": 1, "effective_seconds": 2}
            },
        },
    )
    source = root / "results/benchmark/a/qwen36/round_1"
    source.mkdir(parents=True)
    record = {
        "run_id": "run-a-1",
        "record_complete": True,
        "problem": {"id": "id_a", "time_limit_seconds": 1},
        "model": {"id": "qwen36"},
        "experiment": {"type": "benchmark", "round": 1},
        "call": {"status": "error" if call_error else "success"},
        "generation": None if call_error else {"content": "fixture"},
        "extracted_code": None if call_error else "print(1)\n",
    }
    write_json(source / "result.json", record)
    candidate = source / "candidate.py"
    if not call_error:
        write_json(source / "response.json", {"raw": "fixture"})
        candidate.write_text("print(1)\n", encoding="utf-8")

    baseline = root / "results/judging/baseline"
    judge_path = baseline / "a/qwen36/round_1/judge.json"
    if not call_error:
        judge_path.parent.mkdir(parents=True)
        source_sha256 = digest(source / "result.json")
        candidate_sha256 = digest(candidate)
        write_json(
            judge_path,
            {
                "status": status,
                "source_run_id": "run-a-1",
                "source_result": str((source / "result.json").relative_to(root)),
                "source_sha256": source_sha256,
                "candidate_sha256": candidate_sha256,
                "time_limit_seconds": 1,
                "test_results": [
                    {"status": test_status, "test_case": f"a.in.{number}"}
                    for number, test_status in enumerate(test_statuses, 1)
                ],
            },
        )
    baseline.mkdir(parents=True, exist_ok=True)
    relative_result = str((source / "result.json").relative_to(root))
    entry = {
        "problem_id": "id_a",
        "problem_name": "a",
        "model": "qwen36",
        "round": 1,
        "source_run_id": "run-a-1",
        "source_result": relative_result,
        "source_sha256": digest(source / "result.json"),
        "candidate_path": None if call_error else str(candidate.relative_to(root)),
        "candidate_sha256": None if call_error else digest(candidate),
        "time_limit_seconds": 1,
        "status": "CALL_ERROR" if call_error else status,
        "judge_path": None if call_error else str(judge_path.relative_to(baseline)),
    }
    tests = []
    if not call_error:
        for number in range(1, len(test_statuses) + 1):
            for path in (data / f"a.in.{number}", data / f"a.out.{number}"):
                tests.append({"path": str(path.relative_to(root)), "sha256": digest(path)})
    write_json(
        baseline / "manifest.json",
        {
            "session_id": "baseline",
            "complete": True,
            "judge_sha256": digest(fixture_judging / "engine.py"),
            "judge_process_sha256": digest(fixture_judging / "execution.py"),
            "judge_policy": dict(JUDGE_POLICY),
            "test_data": {"id_a": tests},
            "entries": [entry],
        },
    )
    return problem, source, baseline


def completed_result(status="WA"):
    return {
        "status": status,
        "passed_cases": 0 if status != "AC" else 1,
        "total_cases": 1,
        "max_case_seconds": 0.1,
        "time_limit_seconds": 2,
        "test_results": [{"status": status, "test_case": "a.in.1"}],
    }


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
