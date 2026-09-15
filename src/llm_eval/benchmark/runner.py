import json
from datetime import datetime
from pathlib import Path

from llm_eval.benchmark.prompts import build_round1_prompt, build_round2_prompt
from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem
from llm_eval.llama_cpp import chat

# Final frozen benchmark generation config.
TEMPERATURE = 0
MAX_TOKENS = 8192
REASONING_BUDGET_TOKENS = 2048


def load_round1_answer(
    project_root: Path, problem_name: str, model: str, problem_id: str
) -> str:
    result_path = (
        project_root
        / "results"
        / "benchmark"
        / "round_1"
        / problem_name
        / model
        / "result.json"
    )

    if not result_path.exists():
        raise SystemExit(
            f"\nABORT: Round 2 requires a Round 1 result\npath: {result_path}\n"
        )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected_metadata = {
        "experiment": ("round", 1),
        "model": ("id", model),
        "problem": ("id", problem_id),
    }
    for section, (field, expected) in expected_metadata.items():
        metadata = result.get(section)
        actual = metadata.get(field) if isinstance(metadata, dict) else None
        if actual != expected:
            raise SystemExit(
                f"\nABORT: Round 1 {section}.{field} mismatch\n"
                f"expected: {expected!r}, actual: {actual!r}\n"
                f"path: {result_path}\n"
            )

    previous_answer = result.get("generation", {}).get("content") or ""

    if not previous_answer.strip():
        raise SystemExit(f"\nABORT: Round 1 answer is empty\npath: {result_path}\n")

    return previous_answer



def run_problem(
    project_root: Path,
    problem: dict,
    model: str,
    round_number: int,
    client,
):
    problem_name = problem["name"]

    problem_dir = project_root / problem["problem_dir"]
    statement_path = project_root / problem["statement_path"]
    time_limit_seconds = problem["time_limit_seconds"]

    result_dir = (
        project_root
        / "results"
        / "benchmark"
        / f"round_{round_number}"
        / problem_name
        / model
    )

    if result_dir.exists():
        result_path = result_dir / "result.json"
        try:
            saved = json.loads(result_path.read_text(encoding="utf-8"))
            status = saved["judge"]["status"]
            completed = status in {"AC", "WA", "TLE", "RE", "NO_CODE"}
        except (OSError, ValueError, KeyError, TypeError):
            completed = False

        if completed:
            print(
                f"SKIP: round={round_number} problem={problem['id']} "
                f"model={model} status={status} (이미 완료)"
            )
            return

        raise SystemExit(
            "\nABORT: incomplete benchmark result exists; check before retrying\n"
            f"path: {result_dir}\n"
        )

    statement = statement_path.read_text(encoding="utf-8")

    if round_number == 1:
        prompt = build_round1_prompt(statement)
    else:
        previous_answer = load_round1_answer(
            project_root=project_root,
            problem_name=problem_name,
            model=model,
            problem_id=problem["id"],
        )

        prompt = build_round2_prompt(
            statement=statement, previous_answer=previous_answer
        )

    print("===== Benchmark Run =====")
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", TEMPERATURE)
    print("max_tokens:", MAX_TOKENS)
    print("reasoning_budget_tokens:", REASONING_BUDGET_TOKENS)
    print()

    print("문제 요청...")

    response = chat(
        client,
        model,
        prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        reasoning_budget_tokens=REASONING_BUDGET_TOKENS,
    )

    response_data = response.model_dump()

    choice = response_data["choices"][0]
    message_data = choice["message"]

    response_text = message_data.get("content") or ""
    reasoning_text = message_data.get("reasoning_content") or ""

    code = extract_python_code(response_text)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    result_dir.mkdir(parents=True, exist_ok=False)

    response_path = result_dir / "response.json"

    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(
            response_data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    if code is None:
        judge_result = {
            "status": "NO_CODE",
            "passed_cases": 0,
            "total_cases": None,
            "max_case_seconds": None,
            "time_limit_seconds": time_limit_seconds,
            "test_results": [],
        }

    else:
        candidate_path = result_dir / "candidate.py"
        candidate_path.write_text(code, encoding="utf-8")

        judge_result = judge_problem(
            code_path=candidate_path,
            problem_dir=problem_dir,
            problem_name=problem_name,
            time_limit_seconds=time_limit_seconds,
        )

    usage = response_data.get("usage") or {}
    timings = response_data.get("timings") or {}

    record = {
        "run_id": run_id,
        "experiment": {
            "type": "benchmark",
            "round": round_number,
        },
        "model": {
            "id": model,
            "name": model,
            "runtime": "llama.cpp",
        },
        "problem": {
            "id": problem["id"],
            "name": problem["name"],
            "title": problem["title"],
            "difficulty": problem["difficulty"],
            "time_limit_seconds": time_limit_seconds,
            "memory_limit_mib": problem["memory_limit_mib"],
            "judge_type": problem["judge_type"],
        },
        "generation_config": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        },
        "generation": {
            "finish_reason": choice["finish_reason"],
            "content": response_text,
            "reasoning_content": reasoning_text,
            "usage": usage,
            "timings": timings,
        },
        "metrics": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_tokens_per_second": timings.get("predicted_per_second"),
        },
        "extracted_code": code,
        "judge": judge_result,
    }

    result_path = result_dir / "result.json"

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(
            record,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print()
    print("===== Result =====")
    print("run_id:", run_id)
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("finish_reason:", choice["finish_reason"])
    print("completion_tokens:", usage.get("completion_tokens"))
    print(
        "generation_tokens_per_second:",
        timings.get("predicted_per_second"),
    )
    print("has_code:", code is not None)
    print("judge:", judge_result["status"])
    print(
        "passed:",
        judge_result["passed_cases"],
        "/",
        judge_result["total_cases"],
    )
    print("max_case_seconds:", judge_result["max_case_seconds"])
    print("saved:", result_dir)
