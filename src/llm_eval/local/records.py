"""Local result records; common identity and request fields have one definition."""
from llm_eval.local.client import REASONING_BUDGET_MESSAGE


def build_record(
    run_id, round_number, model, problem, time_limit_seconds, prompt,
    temperature, max_tokens, reasoning_budget_tokens,
):
    return {
        "run_id": run_id,
        "experiment": {"type": "benchmark", "round": round_number},
        "model": {"id": model, "name": model, "runtime": "llama.cpp"},
        "problem": {
            "id": problem["id"], "name": problem["name"], "title": problem["title"],
            "difficulty": problem["difficulty"], "time_limit_seconds": time_limit_seconds,
            "memory_limit_mib": problem["memory_limit_mib"], "judge_type": problem["judge_type"],
        },
        "request": {"messages": [{"role": "user", "content": prompt}]},
        "generation_config": {
            "temperature": temperature, "max_tokens": max_tokens,
            "reasoning_budget_tokens": reasoning_budget_tokens, "cache_prompt": False,
            "reasoning_budget_message": REASONING_BUDGET_MESSAGE,
        },
        "judge": None,
        "record_complete": True,
    }


def build_failure_record(
    run_id, round_number, model, problem, time_limit_seconds, prompt,
    temperature, max_tokens, reasoning_budget_tokens, response_elapsed, exc,
):
    return {
        **build_record(run_id, round_number, model, problem, time_limit_seconds,
                       prompt, temperature, max_tokens, reasoning_budget_tokens),
        "call": {"status": "error", "error": {"type": type(exc).__name__, "message": str(exc)}},
        "generation": None,
        "metrics": {
            "response_elapsed_seconds": response_elapsed, "prompt_tokens": None,
            "completion_tokens": None, "generation_tokens_per_second": None,
        },
        "extracted_code": None,
    }


def build_success_record(
    *, run_id, round_number, model, problem, time_limit_seconds, prompt,
    temperature, max_tokens, reasoning_budget_tokens, response_elapsed,
    choice, response_text, reasoning_text, usage, timings, code,
):
    return {
        **build_record(run_id, round_number, model, problem, time_limit_seconds,
                       prompt, temperature, max_tokens, reasoning_budget_tokens),
        "call": {"status": "success", "error": None},
        "generation": {
            "finish_reason": choice["finish_reason"], "content": response_text,
            "reasoning_content": reasoning_text, "usage": usage, "timings": timings,
        },
        "metrics": {
            "response_elapsed_seconds": response_elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_tokens_per_second": timings.get("predicted_per_second"),
        },
        "extracted_code": code,
    }
