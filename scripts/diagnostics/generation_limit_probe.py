import argparse
import json
from datetime import datetime
from pathlib import Path

from llm_eval.shared.code_extraction import extract_python_code
from llm_eval.local.client import chat, create_client

TEMPERATURE = 0
MAX_TOKENS = 6144
REASONING_BUDGET_TOKENS = 2048


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
        choices=["qwen36", "gemma4"],
    )

    return parser.parse_args()


def main():
    args = parse_args()

    root = Path(__file__).resolve().parents[2]

    statement_path = root / "data/coci/2025_2026/contest5/statements/slaganje.md"

    statement = statement_path.read_text(encoding="utf-8")

    prompt = f"""
다음 알고리즘 문제를 해결하세요.

요구사항:
- 문제 해결 접근법을 설명하세요.
- 시간 복잡도와 공간 복잡도를 설명하세요.
- 실행 가능한 Python 3 정답 코드를 제공하세요.
- 입력은 표준 입력(stdin)에서 받고 출력은 표준 출력(stdout)으로 작성하세요.
- 최종 Python 코드는 ```python 코드 블록 안에 작성하세요.
- 최종 답변에는 실행 가능한 Python 3 코드 블록을 정확히 하나만 포함하세요.
- 중간 코드, 예시 코드, 수정 전 코드는 코드 블록으로 작성하지 마세요.
- 코드 블록 안의 코드는 그대로 제출되므로 자체 수정본이나 대체 코드를 추가로 작성하지 마세요.

문제:

{statement}
""".strip()

    client = create_client()

    print(f"Stress test 시작: {args.model}")

    response = chat(
        client,
        args.model,
        prompt,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        reasoning_budget_tokens=REASONING_BUDGET_TOKENS,
    )

    response_data = response.model_dump()

    choice = response_data["choices"][0]
    message = choice["message"]

    content = message.get("content") or ""
    reasoning_content = message.get("reasoning_content") or ""

    code = extract_python_code(content)

    finish_reason = choice["finish_reason"]

    usage = response_data.get("usage") or {}

    completion_tokens = usage.get("completion_tokens")

    if finish_reason == "stop" and code is not None:
        status = "PASS"
    elif finish_reason == "length":
        status = "LENGTH"
    elif code is None:
        status = "NO_CODE"
    else:
        status = "FAIL"

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    result_dir = (
        root / "results" / "calibration" / "stress" / run_id / args.model / "slaganje"
    )

    result_dir.mkdir(parents=True, exist_ok=False)

    (result_dir / "response.json").write_text(
        json.dumps(
            response_data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    if code is not None:
        (result_dir / "candidate.py").write_text(
            code,
            encoding="utf-8",
        )

    result = {
        "run_id": run_id,
        "type": "generation_stress_test",
        "model": args.model,
        "problem": "slaganje",
        "generation_config": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
            "reasoning_budget_message": (
                "Considering the limited time by the user, "
                "I have to give the solution based on the thinking directly now."
            ),
        },
        "finish_reason": finish_reason,
        "completion_tokens": completion_tokens,
        "has_code": code is not None,
        "status": status,
        "reasoning_content": reasoning_content,
        "content": content,
    }

    (result_dir / "result.json").write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("===== Stress Test Result =====")
    print("model:", args.model)
    print("finish_reason:", finish_reason)
    print("completion_tokens:", completion_tokens)
    print("has_code:", code is not None)
    print("status:", status)
    print("saved:", result_dir)


if __name__ == "__main__":
    main()
