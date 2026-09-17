"""Historical diagnostic requests, intentionally separate from benchmark prompts."""
from openai import OpenAI
from llm_eval.shared.workloads import workload
import json
from datetime import datetime

from llm_eval.local.client import chat, create_client
from llm_eval.shared.code_extraction import extract_python_code

TEMPERATURE = 0
MAX_TOKENS = 6144
REASONING_BUDGET_TOKENS = 2048


def _generation_limit_probe(root, model):
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

    print(f"Stress test 시작: {model}")

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
        root / "results" / "calibration" / "stress" / run_id / model / "slaganje"
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
        "model": model,
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
    print("model:", model)
    print("finish_reason:", finish_reason)
    print("completion_tokens:", completion_tokens)
    print("has_code:", code is not None)
    print("status:", status)
    print("saved:", result_dir)



def _response_probe():
    client = OpenAI(
        base_url="http://127.0.0.1:8080/v1",
        api_key="local",
        timeout=3600,
        max_retries=0,
    )

    r = client.chat.completions.create(
        # model="qwen36",
        model="gemma4",
        messages=[
            {
                "role": "user",
                "content": """
    다음 문제를 Python으로 해결하는 방법을 충분히 자세히 설명하세요.

    정수 n이 주어질 때 1부터 n까지의 합을 출력하세요.
    입력: 1000000
    """,
            }
        ],
        temperature=0,
        max_tokens=1024,
        extra_body={
            "reasoning_budget_tokens": 512,
        },
    )

    print(r.choices[0].message.content)
    print()
    print(r.model_dump().get("timings"))



def run_response_probe(root):
    with workload(root, "local"):
        return _response_probe()


def run_generation_limit_probe(root, model):
    with workload(root, "local"):
        return _generation_limit_probe(root, model)
