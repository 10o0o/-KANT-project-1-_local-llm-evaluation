from pathlib import Path

from llm_eval.judge import judge_problem

result = judge_problem(
    code_path=Path("tmp/struktura_qwen_fixed.py"),
    problem_dir=Path("data/coci/2025_2026/contest5/testdata/struktura"),
    problem_name="struktura",
    time_limit_seconds=1.0,
)

print()
print("최종 판정:", result["status"])
print(
    "통과:",
    result["passed_cases"],
    "/",
    result["total_cases"],
)
print(
    "최대 실행 시간:",
    result["max_case_seconds"],
)
