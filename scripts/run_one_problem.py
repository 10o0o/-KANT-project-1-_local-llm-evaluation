import argparse
import json
from datetime import datetime
from pathlib import Path

from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem
from llm_eval.llama_cpp import chat, create_client
from llm_eval.problems import get_problem, load_problems

# Final frozen benchmark generation config.
TEMPERATURE = 0
MAX_TOKENS = 6144
REASONING_BUDGET_TOKENS = 2048


def parse_args():
    parser = argparse.ArgumentParser(description="Run one local-LLM benchmark problem.")

    parser.add_argument(
        "--model",
        required=True,
        choices=["qwen36", "gemma4"],
        help="Model alias exposed by llama.cpp server.",
    )

    parser.add_argument(
        "--problem",
        required=True,
        help="Problem ID defined in data/coci/problems.json.",
    )

    # Round 2 requires a different self-review prompt and is intentionally
    # disabled until that runner is implemented.
    parser.add_argument(
        "--round",
        required=True,
        type=int,
        choices=[1],
        help="Benchmark round. Currently only Round 1 is implemented.",
    )

    return parser.parse_args()


def build_prompt(statement: str) -> str:
    return f"""
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


def main():
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]

    problems = load_problems(project_root)
    problem = get_problem(problems, args.problem)

    model = args.model
    problem_name = problem["name"]

    problem_dir = project_root / problem["problem_dir"]
    statement_path = project_root / problem["statement_path"]
    time_limit_seconds = problem["time_limit_seconds"]

    result_dir = (
        project_root
        / "results"
        / "benchmark"
        / f"round_{args.round}"
        / problem_name
        / model
    )

    if result_dir.exists():
        raise SystemExit(
            "\nABORT: benchmark result already exists\n"
            f"round   : {args.round}\n"
            f"model   : {model}\n"
            f"problem : {problem['id']}\n"
            f"path    : {result_dir}\n"
        )

    statement = statement_path.read_text(encoding="utf-8")
    prompt = build_prompt(statement)

    print("===== Benchmark Run =====")
    print("round:", args.round)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", TEMPERATURE)
    print("max_tokens:", MAX_TOKENS)
    print("reasoning_budget_tokens:", REASONING_BUDGET_TOKENS)
    print()

    client = create_client()

    print("문제 요청...")

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
    message_data = choice["message"]

    response_text = message_data.get("content") or ""
    reasoning_text = message_data.get("reasoning_content") or ""

    code = extract_python_code(response_text)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    result_dir.mkdir(parents=True, exist_ok=False)

    response_path = result_dir / "response.json"

    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(
            response_data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

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

    record = {
        "run_id": run_id,
        "experiment": {
            "type": "benchmark",
            "round": args.round,
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
        "generation_config": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "reasoning_budget_tokens": REASONING_BUDGET_TOKENS,
        },
        "generation": {
            "finish_reason": choice["finish_reason"],
            "content": response_text,
            "reasoning_content": reasoning_text,
            "usage": usage,
            "timings": timings,
        },
        "metrics": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "generation_tokens_per_second": timings.get("predicted_per_second"),
        },
        "extracted_code": code,
        "judge": judge_result,
    }

    result_path = result_dir / "result.json"

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(
            record,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print()
    print("===== Result =====")
    print("run_id:", run_id)
    print("round:", args.round)
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


if __name__ == "__main__":
    main()
