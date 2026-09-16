def print_benchmark_run(
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


def build_failure_record(
    run_id,
    round_number,
    model,
    problem,
    time_limit_seconds,
    prompt,
    temperature,
    max_tokens,
    reasoning_budget_tokens,
    response_elapsed,
    exc,
):
    return {
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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_budget_tokens": reasoning_budget_tokens,
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


def build_success_record(
    *,
    run_id,
    round_number,
    model,
    problem,
    time_limit_seconds,
    prompt,
    temperature,
    max_tokens,
    reasoning_budget_tokens,
    response_elapsed,
    choice,
    response_text,
    reasoning_text,
    usage,
    timings,
    code,
    judge_result,
):
    return {
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
            "temperature": temperature,
            "max_tokens": max_tokens,
            "reasoning_budget_tokens": reasoning_budget_tokens,
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


def print_benchmark_result(
    *,
    run_id,
    round_number,
    model,
    problem,
    choice,
    usage,
    timings,
    code,
    judge_result,
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
