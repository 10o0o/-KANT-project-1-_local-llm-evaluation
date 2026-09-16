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
from llm_eval.records import write_json, generation_complete
from llm_eval.llama_cpp import REASONING_BUDGET_MESSAGE, chat
from llm_eval.runtime import measured_metrics, safe_memory

# Final frozen benchmark generation config.
TEMPERATURE = 0

MAX_TOKENS = 61440
REASONING_BUDGET_TOKENS = 53248


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

    statement = statement_path.read_text(encoding="utf-8")
    prompt = build_round1_prompt(
        statement,
        time_limit_seconds=time_limit_seconds,
        memory_limit_mib=problem["memory_limit_mib"],
    )
    expected_request = {"messages": [{"role": "user", "content": prompt}]}
    expected_config = {
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        "cache_prompt": False,
        "reasoning_budget_message": REASONING_BUDGET_MESSAGE,
    }

    if result_dir.exists():
        result_path = result_dir / "result.json"
        try:
            saved = json.loads(result_path.read_text(encoding="utf-8"))

            if not isinstance(saved, dict):
                raise ValueError("Invalid result record")
            if (
                saved.get("request") != expected_request
                or saved.get("generation_config") != expected_config
                or saved.get("model", {}).get("id") != model
                or saved.get("problem", {}).get("id") != problem["id"]
                or saved.get("experiment") != {"type": "benchmark", "round": round_number}
            ):
                raise SystemExit(
                    f"ABORT: 기존 요청과 현재 입력·설정이 다릅니다: {result_path}"
                )
            call_status = saved.get("call", {}).get("status")

            status = "CALL_ERROR" if call_status == "error" else "생성 완료·채점 대기"
            completed = generation_complete(saved)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
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

        write_json(result_path, failure_record)
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

    if code is not None:
        candidate_path = result_dir / "candidate.py"
        candidate_path.write_text(code, encoding="utf-8")

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
    )

    record["metrics"] = measured_metrics(response_elapsed, usage, timings, memory)

    write_json(result_path, record)

    print_benchmark_result(
        run_id=run_id,
        round_number=round_number,
        model=model,
        problem=problem,
        choice=choice,
        usage=usage,
        metrics=record["metrics"],
        code=code,
        result_dir=result_dir,
    )
