import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from llm_eval.benchmark.prompts import build_round1_prompt
from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem
from llm_eval.llama_cpp import chat

# Final frozen benchmark generation config.
TEMPERATURE = 0
MAX_TOKENS = 8192
REASONING_BUDGET_TOKENS = 2048


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

            call_status = saved.get("call", {}).get("status")

            if call_status == "error":
                status = "CALL_ERROR"
                completed = True
            else:
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

    prompt = build_round1_prompt(statement)

    print("===== Benchmark Run =====")
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", TEMPERATURE)
    print("max_tokens:", MAX_TOKENS)
    print("reasoning_budget_tokens:", REASONING_BUDGET_TOKENS)
    print()

    print("문제 요청...")

    response_start = perf_counter()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result_dir.mkdir(parents=True, exist_ok=False)
    response_path = result_dir / "response.json"
    result_path = result_dir / "result.json"

    try:
        response = chat(
            client,
            model,
            prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            reasoning_budget_tokens=REASONING_BUDGET_TOKENS,
        )
    except Exception as exc:
        response_elapsed = perf_counter() - response_start
        print("호출 실패:", type(exc).__name__)
        print("실패까지 걸린 시간:", response_elapsed)

        failure_record = {
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
            "request": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            "generation_config": {
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
            },
            "call": {
                "status": "error",
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            },
            "generation": None,
            "metrics": {
                "response_elapsed_seconds": response_elapsed,
                "prompt_tokens": None,
                "completion_tokens": None,
                "generation_tokens_per_second": None,
            },
            "extracted_code": None,
            "judge": None,
        }

        result_path.write_text(
            json.dumps(
                failure_record,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        raise

    response_elapsed = perf_counter() - response_start

    response_data = response.model_dump()

    choice = response_data["choices"][0]
    message_data = choice["message"]

    response_text = message_data.get("content") or ""
    reasoning_text = message_data.get("reasoning_content") or ""

    code = extract_python_code(response_text)

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
        "request": {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        },
        "generation_config": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        },
        "call": {
            "status": "success",
            "error": None,
        },
        "generation": {
            "finish_reason": choice["finish_reason"],
            "content": response_text,
            "reasoning_content": reasoning_text,
            "usage": usage,
            "timings": timings,
        },
        "metrics": {
            "response_elapsed_seconds": response_elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_tokens_per_second": timings.get("predicted_per_second"),
        },
        "extracted_code": code,
        "judge": judge_result,
    }

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
