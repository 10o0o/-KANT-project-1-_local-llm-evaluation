import argparse
from pathlib import Path

from llm_eval.judge import judge_problem
from llm_eval.problems import get_problem, load_problems


def main():
    parser = argparse.ArgumentParser(description="수정한 candidate 코드 채점")
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--problem", required=True)

    args = parser.parse_args()

    print("코드 경로:", args.code)
    print("문제 ID:", args.problem)

    project_root = Path(__file__).resolve().parents[1]

    problems = load_problems(project_root)
    problem = get_problem(problems, args.problem)

    problem_dir = project_root / problem["problem_dir"]

    print("문제 이름:", problem["name"])
    print("테스트 경로:", problem_dir)
    print("시간 제한:", problem["time_limit_seconds"])

    code_path = args.code.resolve()

    if not code_path.is_file():
        parser.error(f"코드 파일을 찾을 수 없습니다: {code_path}")

    if problem["judge_type"] != "token":
        parser.error("현재는 token 방식의 문제만 지원합니다.")

    result = judge_problem(
        code_path=code_path,
        problem_dir=problem_dir,
        problem_name=problem["name"],
        time_limit_seconds=problem["time_limit_seconds"],
    )

    print()
    print("최종 판정:", result["status"])
    print("통과:", result["passed_cases"], "/", result["total_cases"])
    print("최대 실행 시간:", result["max_case_seconds"])


if __name__ == "__main__":
    main()
