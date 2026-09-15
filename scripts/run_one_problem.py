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
MAX_TOKENS = 8192
REASONING_BUDGET_TOKENS = 2048


def parse_args():
    parser = argparse.ArgumentParser(description="Run selected local-LLM benchmark problems.")

    parser.add_argument(
        "--model",
        required=True,
        choices=["qwen36", "gemma4"],
        help="Model alias exposed by llama.cpp server.",
    )

    parser.add_argument(
        "--problems",
        required=True,
        help="Comma-separated problem IDs, or 'all'.",
    )

    # Round 2 reviews the same model's Round 1 answer without judge feedback.
    parser.add_argument(
        "--round",
        required=True,
        type=int,
        choices=[1, 2],
        help="Benchmark round.",
    )

    return parser.parse_args()


def select_problems(problems: list[dict], selection: str) -> list[dict]:
    selection = selection.strip()

    if selection == "all":
        return problems

    problem_ids = [problem_id.strip() for problem_id in selection.split(",")]

    return [get_problem(problems, problem_id) for problem_id in problem_ids]


def build_round2_prompt(statement: str, previous_answer: str) -> str:
    return f"""
        다음 알고리즘 문제와 이전 답변을 다시 검토하세요.

        중요:
        - 이전 답변이 맞거나 틀렸다고 미리 가정하지 마세요.
        - 외부 채점 결과나 정답 여부에 대한 정보는 제공되지 않습니다.
        - 문제 조건과 이전 답변만을 바탕으로 스스로 검증하세요.

        검토 요구사항:
        - 문제 조건을 처음부터 다시 확인하세요.
        - 알고리즘의 논리적 오류와 누락된 경계 조건을 확인하세요.
        - 시간 복잡도와 공간 복잡도가 제한 안에서 적절한지 확인하세요.
        - 설명과 실제 구현이 서로 일치하는지 확인하세요.
        - 구현상의 인덱스, 수식, 자료형, 입출력, 예외 조건 오류를 확인하세요.
        - 오류가 있다고 판단하면 수정하세요.
        - 오류가 없다고 판단하면 기존 핵심 접근을 유지해도 됩니다.
        - 최종적으로 문제 해결 접근법을 설명하세요.
        - 시간 복잡도와 공간 복잡도를 설명하세요.
        - 실행 가능한 Python 3 정답 코드를 제공하세요.
        - 입력은 표준 입력(stdin)에서 받고 출력은 표준 출력(stdout)으로 작성하세요.
        - 최종 Python 코드는 ```python 코드 블록 안에 작성하세요.
        - 최종 답변에는 실행 가능한 Python 3 코드 블록을 정확히 하나만 포함하세요.
        - 중간 코드, 예시 코드, 수정 전 코드는 코드 블록으로 작성하지 마세요.
        - 코드 블록 안의 코드는 그대로 제출되므로 자체 수정본이나 대체 코드를 추가로 작성하지 마세요.

        문제:

        {statement}

        이전 답변:

        --- BEGIN ROUND 1 ANSWER ---
        {previous_answer}
        --- END ROUND 1 ANSWER ---
        """.strip()


def load_round1_answer(project_root: Path, problem_name: str, model: str) -> str:
    result_path = (
        project_root
        / "results"
        / "benchmark"
        / "round_1"
        / problem_name
        / model
        / "result.json"
    )

    if not result_path.exists():
        raise SystemExit(
            f"\nABORT: Rount 2 requires a Round 1 result\npath: {result_path}\ns"
        )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    previous_answer = result.get("generation", {}).get("content") or ""

    if not previous_answer.strip():
        raise SystemExit(f"\nABORT: Round 1 answer is empty\npath: {result_path}\n")

    return previous_answer


def build_round1_prompt(statement: str) -> str:
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


def run_problem(
    project_root: Path,
    problem: dict,
    model: str,
    round_number: int,
    client,
):
    problem_name = problem["name"]

    problem_dir = project_root / problem["problem_dir"]
    statement_path = project_root / problem["statement_path"]
    time_limit_seconds = problem["time_limit_seconds"]

    result_dir = (
        project_root
        / "results"
        / "benchmark"
        / f"round_{round_number}"
        / problem_name
        / model
    )

    if result_dir.exists():
        result_path = result_dir / "result.json"
        try:
            saved = json.loads(result_path.read_text(encoding="utf-8"))
            status = saved["judge"]["status"]
            completed = status in {"AC", "WA", "TLE", "RE", "NO_CODE"}
        except (OSError, ValueError, KeyError, TypeError):
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

    statement = statement_path.read_text(encoding="utf-8")

    if round_number == 1:
        prompt = build_round1_prompt(statement)
    else:
        previous_answer = load_round1_answer(
            project_root=project_root, problem_name=problem_name, model=model
        )

        prompt = build_round2_prompt(
            statement=statement, previous_answer=previous_answer
        )

    print("===== Benchmark Run =====")
    print("round:", round_number)
    print("model:", model)
    print("problem:", problem["id"])
    print("temperature:", TEMPERATURE)
    print("max_tokens:", MAX_TOKENS)
    print("reasoning_budget_tokens:", REASONING_BUDGET_TOKENS)
    print()

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


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    problems = load_problems(project_root)
    selected_problems = select_problems(problems, args.problems)

    print("선택한 문제:")
    for problem in selected_problems:
        print("-", problem["id"])

    with create_client() as client:
        for problem in selected_problems:
            run_problem(
                project_root=project_root,
                problem=problem,
                model=args.model,
                round_number=args.round,
                client=client,
            )


if __name__ == "__main__":
    main()
