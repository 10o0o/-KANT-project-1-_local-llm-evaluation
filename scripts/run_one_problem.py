import json
from datetime import datetime
from pathlib import Path

from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem
from llm_eval.llama_cpp import chat, create_client

# MODEL = "qwen36-35b-lowvram:latest"
# MODEL_NAME = "qwen36"
# MODEL = "gemma4:26b-a4b-it-q4_K_M"
MODEL = "gemma4"
MODEL_NAME = "gemma4"

PROBLEM_NAME = "skare"
TIME_LIMIT_SECONDS = 3.0


def main():
    project_root = Path(__file__).resolve().parents[1]

    problem_dir = (
        project_root
        / "data"
        / "coci"
        / "2025_2026"
        / "contest5"
        / "testdata"
        / PROBLEM_NAME
    )

    statement_path = (
        project_root
        / "data"
        / "coci"
        / "2025_2026"
        / "contest5"
        / "statements"
        / f"{PROBLEM_NAME}.md"
    )

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

    # options = {
    #     "temperature": 0,
    #     "num_predict": 8192,
    #     "num_ctx": 16384,
    # }

    # print("모델 워밍업...")
    # warm_up(client, MODEL)

    print("문제 요청...")
    response = chat(
        client,
        MODEL,
        prompt,
        temperature=0,
        max_tokens=4096,
        reasoning_budget_tokens=2048,
    )

    response_data = response.model_dump()
    print(json.dumps(response_data, ensure_ascii=False, indent=2))

    message_data = response_data["choices"][0]["message"]

    response_text = message_data.get("content") or ""
    reasoning_text = message_data.get("reasoning_content") or ""

    print("\n===== 모델 Thinking =====\n")
    print(reasoning_text)

    print("\n===== 모델 최종 답변 =====\n")
    print(response_text)

    print("\n===== 모델 원본 답변 =====\n")
    print(response_text)

    code = extract_python_code(response_text)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result_dir = project_root / "results" / run_id / MODEL_NAME / PROBLEM_NAME
    result_dir.mkdir(parents=True, exist_ok=False)

    response_path = result_dir / "response.json"

    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(
            response.model_dump(),
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    if code is None:
        print("\nPython 코드를 찾지 못했습니다: NO_CODE")
        return

    candidate_path = result_dir / "candidate.py"
    candidate_path.write_text(code, encoding="utf-8")

    print("\n===== 추출된 코드 =====\n")
    print(code)

    judge_result = judge_problem(
        code_path=candidate_path,
        problem_dir=problem_dir,
        problem_name=PROBLEM_NAME,
        time_limit_seconds=TIME_LIMIT_SECONDS,
    )

    print("\n===== 채점 결과 =====")
    print("최종 판정:", judge_result["status"])
    print(
        "통과:",
        judge_result["passed_cases"],
        "/",
        judge_result["total_cases"],
    )
    print(
        "최대 실행 시간:",
        judge_result["max_case_seconds"],
    )

    judge_path = result_dir / "judge.json"

    with open(judge_path, "w", encoding="utf-8") as f:
        record = {
            "model": MODEL,
            "problem": PROBLEM_NAME,
            "settings": {
                "temperature": 0,
                "max_tokens": 4096,
                "reasoning_budget_tokens": 2048,
            },
            "response": response_data,
        }

        json.dump(
            record,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        # json.dump(
        #     judge_result,
        #     f,
        #     ensure_ascii=False,
        #     indent=2,
        # )

    # client.generate(
    #     model=MODEL,
    #     prompt="",
    #     keep_alive=0,
    # )


if __name__ == "__main__":
    main()
