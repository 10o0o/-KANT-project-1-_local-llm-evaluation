import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from llm_eval.shared.prompts import build_problem_prompt
from llm_eval.local.records import build_record, build_failure_record, build_success_record
from llm_eval.shared.paths import generation_dir
from llm_eval.shared.code_extraction import extract_python_code
from llm_eval.shared.storage import write_json, write_text
from llm_eval.shared.artifacts import validate_artifacts
from llm_eval.local.client import REASONING_BUDGET_MESSAGE, chat
from llm_eval.local.metrics import measured_metrics, safe_memory

# Final frozen benchmark generation config.
TEMPERATURE = 0

MAX_TOKENS = 61440
REASONING_BUDGET_TOKENS = 53248


def request_conditions(project_root, problem):
    statement = (project_root / problem["statement_path"]).read_text(encoding="utf-8")
    prompt = build_problem_prompt(
        statement, time_limit_seconds=problem["time_limit_seconds"],
        memory_limit_mib=problem["memory_limit_mib"],
    )
    return {"messages": [{"role": "user", "content": prompt}]}, {
        "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
        "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        "cache_prompt": False, "reasoning_budget_message": REASONING_BUDGET_MESSAGE,
    }


def inspect_existing(result_dir, problem, model, round_number, request, config):
    """Read-only resume contract shared by the runner and unattended queue."""
    if not result_dir.exists():
        return None
    result_path = result_dir / "result.json"
    try:
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise ValueError("Invalid result record")
        if (
            saved.get("request") != request or saved.get("generation_config") != config
            or saved.get("model", {}).get("id") != model
            or saved.get("problem", {}).get("id") != problem["id"]
            or saved.get("experiment") != {"type": "benchmark", "round": round_number}
        ):
            raise SystemExit(f"ABORT: 기존 요청과 현재 입력·설정이 다릅니다: {result_path}")
        validate_artifacts(result_dir, saved)
        return saved
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise SystemExit(f"ABORT: incomplete benchmark result exists; check before retrying\npath: {result_dir}") from exc


def run_problem(
    project_root: Path,
    problem: dict,
    model: str,
    round_number: int,
    client,
):
    time_limit_seconds = problem["time_limit_seconds"]
    result_dir = generation_dir(project_root, problem["name"], model, round_number)

    expected_request, expected_config = request_conditions(project_root, problem)
    prompt = expected_request["messages"][0]["content"]
    saved = inspect_existing(result_dir, problem, model, round_number, expected_request, expected_config)
    if saved is not None:
        print(f"SKIP: round={round_number} problem={problem['id']} model={model} (이미 기록한 시도)")
        return

    _print_run(
        round_number, model, problem, TEMPERATURE, MAX_TOKENS, REASONING_BUDGET_TOKENS
    )

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ")
    result_dir.mkdir(parents=True, exist_ok=False)
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
    save_response(result_dir, response, response_elapsed, run_id,
                  round_number, model, problem, prompt)


def _print_run(
    round_number, model, problem, temperature, max_tokens, reasoning_budget_tokens
):
    print("===== Benchmark Run =====")
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", temperature)
    print("max_tokens:", max_tokens)
    print("reasoning_budget_tokens:", reasoning_budget_tokens)
    print()

    print("문제 요청...")



def _print_result(
    *,
    run_id,
    round_number,
    model,
    problem,
    choice,
    usage,
    metrics,
    code,
    result_dir,
):
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
        metrics.get("generation_tokens_per_second"),
    )
    print("has_code:", code is not None)
    print("생성 완료·채점 대기")
    print("saved:", result_dir)


def save_response(result_dir, response, response_elapsed, run_id, round_number, model, problem, prompt):
    """Persist a received response; a partial write must never authorize a retry."""
    time_limit_seconds = problem["time_limit_seconds"]
    response_path = result_dir / "response.json"
    result_path = result_dir / "result.json"
    record = build_record(run_id, round_number, model, problem, time_limit_seconds,
                          prompt, TEMPERATURE, MAX_TOKENS, REASONING_BUDGET_TOKENS)
    record.update(call={"status": "success", "error": None}, generation=None,
                  extracted_code=None, record_complete=False,
                  metrics=measured_metrics(response_elapsed, {}, {}, {}))
    stage = "serialize_response"
    try:
        stage = "serialize_response"
        response_data = response.model_dump()

        stage = "save_response"
        write_json(response_path, response_data)

        memory = safe_memory(None, "response_received", model=model)

        stage = "extract_response"
        choice = response_data["choices"][0]
        message_data = choice["message"]

        response_text = message_data.get("content") or ""
        reasoning_text = message_data.get("reasoning_content") or ""

        code = extract_python_code(response_text)

        if code is not None:
            candidate_path = result_dir / "candidate.py"
            stage = "save_candidate"
            write_text(candidate_path, code)

        usage = response_data.get("usage") or {}
        timings = response_data.get("timings") or {}

        stage = "build_record"
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

        stage = "save_record"
        write_json(result_path, record)
    except Exception as exc:
        record["record_complete"] = False
        record["processing_error"] = {"stage": stage, "type": type(exc).__name__}
        try:
            write_json(result_path, record)
        except Exception:
            pass  # Exclusive directory reservation still prevents a second call.
        raise

    _print_result(
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
