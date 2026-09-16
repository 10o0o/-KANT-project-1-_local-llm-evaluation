import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from llm_eval.llama_cpp import chat

WARMUP_PROMPT = "워밍업 요청입니다. 최종 답변으로 WARMUP_OK라고만 답하세요."
WARMUP_TEMPERATURE = 0
WARMUP_MAX_TOKENS = 128
WARMUP_REASONING_BUDGET_TOKENS = 64


def run_warmup(
    project_root: Path,
    model: str,
    client,
):
    result_dir = project_root / "results" / "warmup" / model

    if result_dir.exists():
        raise SystemExit(f"\nABORT: warmup result already exists\npath: {result_dir}\n")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    result_dir.mkdir(parents=True, exist_ok=False)

    result_path = result_dir / "result.json"
    response_path = result_dir / "response.json"

    response_start = perf_counter()

    try:
        response = chat(
            client,
            model,
            WARMUP_PROMPT,
            temperature=WARMUP_TEMPERATURE,
            max_tokens=WARMUP_MAX_TOKENS,
            reasoning_budget_tokens=WARMUP_REASONING_BUDGET_TOKENS,
        )
    except Exception as exc:
        response_elapsed = perf_counter() - response_start

        failure_record = {
            "run_id": run_id,
            "experiment": {
                "type": "warmup",
            },
            "model": {
                "id": model,
                "name": model,
                "runtime": "llama.cpp",
            },
            "request": {
                "messages": [
                    {
                        "role": "user",
                        "content": WARMUP_PROMPT,
                    }
                ],
            },
            "generation_config": {
                "temperature": WARMUP_TEMPERATURE,
                "max_tokens": WARMUP_MAX_TOKENS,
                "reasoning_budget_tokens": WARMUP_REASONING_BUDGET_TOKENS,
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

    response_path.write_text(
        json.dumps(
            response_data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    choice = response_data["choices"][0]
    message = choice["message"]

    usage = response_data.get("usage") or {}
    timings = response_data.get("timings") or {}

    record = {
        "run_id": run_id,
        "experiment": {
            "type": "warmup",
        },
        "model": {
            "id": model,
            "name": model,
            "runtime": "llama.cpp",
        },
        "request": {
            "messages": [
                {
                    "role": "user",
                    "content": WARMUP_PROMPT,
                }
            ],
        },
        "generation_config": {
            "temperature": WARMUP_TEMPERATURE,
            "max_tokens": WARMUP_MAX_TOKENS,
            "reasoning_budget_tokens": WARMUP_REASONING_BUDGET_TOKENS,
        },
        "call": {
            "status": "success",
            "error": None,
        },
        "generation": {
            "finish_reason": choice["finish_reason"],
            "content": message.get("content") or "",
            "reasoning_content": message.get("reasoning_content") or "",
            "usage": usage,
            "timings": timings,
        },
        "metrics": {
            "response_elapsed_seconds": response_elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_tokens_per_second": timings.get("predicted_per_second"),
        },
    }

    result_path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("===== Warmup Result =====")
    print("model:", model)
    print("finish_reason:", choice["finish_reason"])
    print("response_elapsed_seconds:", response_elapsed)
    print(
        "generation_tokens_per_second:",
        timings.get("predicted_per_second"),
    )
    print("saved:", result_dir)
