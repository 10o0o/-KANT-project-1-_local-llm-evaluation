from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from llm_eval.shared.problems import problem_prompt
from llm_eval.shared.artifacts import (
    generation_dir,
    read_generation_record,
    reset_demo_dir,
    validate_artifacts,
)
from llm_eval.shared.code_extraction import extract_python_code
from llm_eval.shared.storage import write_json, write_text
from llm_eval.local.client import (
    chat,
    create_client,
    generation_config,
)
from llm_eval.local.metrics import measured_metrics, safe_memory
from llm_eval.shared.problems import load_problems, select_problems
from llm_eval.shared.workloads import workload

def build_record(
    run_id,
    round_number,
    model,
    problem,
    time_limit_seconds,
    prompt,
    config,
):
    experiment = (
        {"type": "demo", "round": None}
        if round_number is None
        else {"type": "benchmark", "round": round_number}
    )
    return {
        "run_id": run_id,
        "experiment": experiment,
        "model": {"id": model, "name": model, "runtime": "llama.cpp"},
        "problem": {
            "id": problem["id"],
            "name": problem["name"],
            "title": problem["title"],
            "difficulty": problem["difficulty"],
            "time_limit_seconds": time_limit_seconds,
            "memory_limit_mib": problem["memory_limit_mib"],
            "judge_type": problem["judge_type"],
        },
        "request": {"messages": [{"role": "user", "content": prompt}]},
        "generation_config": dict(config),
        "judge": None,
        "record_complete": True,
    }


def request_conditions(project_root, problem):
    prompt = problem_prompt(project_root, problem)
    return {"messages": [{"role": "user", "content": prompt}]}, generation_config()


def inspect_existing(result_dir, problem, model, round_number, request, config):
    """Read-only resume contract shared by the runner and unattended queue."""
    if not result_dir.exists():
        return None
    result_path = result_dir / "result.json"
    try:
        saved = read_generation_record(result_path)
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


def preflight_problem(project_root, problem, model, round_number):
    request, config = request_conditions(project_root, problem)
    folder = generation_dir(project_root, problem["name"], model, round_number)
    record = inspect_existing(folder, problem, model, round_number, request, config)
    if record is None:
        return "missing"
    return "complete" if record["call"]["status"] == "success" else "failed"


def run_problem(
    project_root: Path,
    problem: dict,
    model: str,
    round_number: int | None,
    client,
):
    time_limit_seconds = problem["time_limit_seconds"]
    result_dir = generation_dir(project_root, problem["name"], model, round_number)

    expected_request, expected_config = request_conditions(project_root, problem)
    prompt = expected_request["messages"][0]["content"]
    if round_number is None:
        result_dir = reset_demo_dir(project_root, problem["name"], model)
    else:
        saved = inspect_existing(
            result_dir,
            problem,
            model,
            round_number,
            expected_request,
            expected_config,
        )
        if saved is not None:
            print(f"SKIP: round={round_number} problem={problem['id']} model={model} (이미 기록한 시도)")
            return

    _print_run(
        round_number,
        model,
        problem,
        expected_config["temperature"],
        expected_config["max_tokens"],
        expected_config["reasoning_budget_tokens"],
        result_dir,
    )

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ")
    if round_number is not None:
        result_dir.mkdir(parents=True, exist_ok=False)
    result_path = result_dir / "result.json"
    response_start = perf_counter()

    try:
        response = chat(
            client,
            model,
            prompt,
            temperature=expected_config["temperature"],
            max_tokens=expected_config["max_tokens"],
            reasoning_budget_tokens=expected_config["reasoning_budget_tokens"],
            cache_prompt=expected_config["cache_prompt"],
            reasoning_budget_message=expected_config["reasoning_budget_message"],
        )
    except Exception as exc:
        response_elapsed = perf_counter() - response_start
        memory = safe_memory(None, "call_error", model=model)
        print("호출 실패:", type(exc).__name__)
        print("실패까지 걸린 시간:", response_elapsed)

        failure_record = build_record(
            run_id, round_number, model, problem, time_limit_seconds, prompt,
            expected_config,
        )
        failure_record.update(
            call={
                "status": "error",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
            generation=None,
            metrics=measured_metrics(response_elapsed, {}, {}, memory),
            extracted_code=None,
        )

        write_json(result_path, failure_record)
        raise

    response_elapsed = perf_counter() - response_start
    save_response(
        result_dir,
        response,
        response_elapsed,
        run_id,
        round_number,
        model,
        problem,
        prompt,
        expected_config,
    )


def _print_run(
    round_number,
    model,
    problem,
    temperature,
    max_tokens,
    reasoning_budget_tokens,
    result_dir,
):
    mode = "demo" if round_number is None else "benchmark"
    heading = "===== Demo Run =====" if round_number is None else "===== Benchmark Run ====="
    print(heading)
    print("mode:", mode)
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", temperature)
    print("max_tokens:", max_tokens)
    print("reasoning_budget_tokens:", reasoning_budget_tokens)
    print("saved:", result_dir)
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


def save_response(
    result_dir,
    response,
    response_elapsed,
    run_id,
    round_number,
    model,
    problem,
    prompt,
    config,
):
    """Persist a received response; a partial write must never authorize a retry."""
    time_limit_seconds = problem["time_limit_seconds"]
    response_path = result_dir / "response.json"
    result_path = result_dir / "result.json"
    record = build_record(run_id, round_number, model, problem, time_limit_seconds,
                          prompt, config)
    record.update(call={"status": "success", "error": None}, generation=None,
                  extracted_code=None, record_complete=False,
                  metrics={"response_elapsed_seconds": response_elapsed})
    stage = "serialize_response"
    try:
        stage = "serialize_response"
        response_data = response.model_dump()

        stage = "save_response"
        write_json(response_path, response_data)

        memory = safe_memory(None, "response_received", model=model)

        usage = response_data.get("usage") or {}
        timings = response_data.get("timings") or {}
        record["metrics"] = measured_metrics(response_elapsed, usage, timings, memory)

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

        stage = "build_record"
        record.update(
            call={"status": "success", "error": None},
            generation={
                "finish_reason": choice["finish_reason"],
                "content": response_text,
                "reasoning_content": reasoning_text,
                "usage": usage,
                "timings": timings,
            },
            extracted_code=code,
            record_complete=True,
        )

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


def run_selected(
    project_root: Path, model: str, selection: str, round_number: int | None = None
):
    if model not in {"qwen36", "gemma4"}:
        raise ValueError(f"지원하지 않는 로컬 모델: {model}")
    if round_number is not None and (
        type(round_number) is not int or round_number not in (1, 2)
    ):
        raise ValueError(f"잘못된 로컬 회차: {round_number}; 생략 또는 1 또는 2")
    with workload(project_root, "local", allow_inherited=True):
        selected_problems = select_problems(load_problems(project_root), selection)
        print("선택한 문제:")
        for problem in selected_problems:
            print("-", problem["id"])
        with create_client() as client:
            for problem in selected_problems:
                run_problem(project_root, problem, model, round_number, client)
