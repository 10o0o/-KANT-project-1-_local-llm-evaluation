import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from llm_eval.benchmark.prompts import build_round1_prompt
from llm_eval.benchmark.utils import (
    build_failure_record,
    build_success_record,
    prepare_problem_context,
    print_benchmark_result,
    print_benchmark_run,
)
from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem
from llm_eval.llama_cpp import chat
from llm_eval.runtime import measured_metrics, safe_memory

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
    (
        problem_name,
        problem_dir,
        statement_path,
        time_limit_seconds,
        result_dir,
    ) = prepare_problem_context(project_root, problem, model, round_number)

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
    print_benchmark_run(
        round_number, model, problem, TEMPERATURE, MAX_TOKENS, REASONING_BUDGET_TOKENS
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result_dir.mkdir(parents=True, exist_ok=False)
    response_path = result_dir / "response.json"
    result_path = result_dir / "result.json"
    response_start = perf_counter()

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
        memory = safe_memory(None, "call_error", model=model)
        print("호출 실패:", type(exc).__name__)
        print("실패까지 걸린 시간:", response_elapsed)

        failure_record = build_failure_record(
            run_id,
            round_number,
            model,
            problem,
            time_limit_seconds,
            prompt,
            TEMPERATURE,
            MAX_TOKENS,
            REASONING_BUDGET_TOKENS,
            response_elapsed,
            exc,
        )

        failure_record["metrics"] = measured_metrics(response_elapsed, {}, {}, memory)

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

    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(
            response_data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    memory = safe_memory(None, "response_received", model=model)

    choice = response_data["choices"][0]
    message_data = choice["message"]

    response_text = message_data.get("content") or ""
    reasoning_text = message_data.get("reasoning_content") or ""

    code = extract_python_code(response_text)

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

    record = build_success_record(
        run_id=run_id,
        round_number=round_number,
        model=model,
        problem=problem,
        time_limit_seconds=time_limit_seconds,
        prompt=prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        reasoning_budget_tokens=REASONING_BUDGET_TOKENS,
        response_elapsed=response_elapsed,
        choice=choice,
        response_text=response_text,
        reasoning_text=reasoning_text,
        usage=usage,
        timings=timings,
        code=code,
        judge_result=judge_result,
    )

    record["metrics"] = measured_metrics(response_elapsed, usage, timings, memory)

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(
            record,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print_benchmark_result(
        run_id=run_id,
        round_number=round_number,
        model=model,
        problem=problem,
        choice=choice,
        usage=usage,
        metrics=record["metrics"],
        code=code,
        judge_result=judge_result,
        result_dir=result_dir,
    )
