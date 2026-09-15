import subprocess
import sys
from pathlib import Path
from time import perf_counter


def run_test_case(
    code_path: Path, input_path: Path, output_path: Path, time_limit_seconds: float
):
    with open(input_path, mode="r", encoding="utf-8") as f:
        input_text = f.read()

    with open(output_path, "r", encoding="utf-8") as f:
        expected_output = f.read()

    # print("INPUT:")
    # print(input_text)

    # print("EXPECTED:")
    # print(expected_output)

    start = perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, str(code_path)],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=time_limit_seconds,
        )
    except subprocess.TimeoutExpired:
        elapsed = perf_counter() - start
        # print("판정: TLE")
        # print("실행 시간:", elapsed)
        return {
            "status": "TLE",
            "elapsed_seconds": elapsed,
            "return_code": None,
            "stdout": "",
            "stderr": "",
        }

    elapsed = perf_counter() - start

    # print("실행 결과:", completed.stdout)
    # print("정답:", expected_output)
    # print("return code:", completed.returncode)
    # print("실행 시간:", elapsed)

    actual_tokens = completed.stdout.split()
    expected_tokens = expected_output.split()

    # if actual_tokens == expected_tokens:
    #     status = "AC"
    # else:
    #     status = "WA"

    if completed.returncode != 0:
        status = "RE"
    elif actual_tokens == expected_tokens:
        status = "AC"
    else:
        status = "WA"

    # print("판정:", status)
    # print("실행 시간:", elapsed)
    # print(f"completed.stderr: {completed.stderr}")

    return {
        "status": status,
        "elapsed_seconds": elapsed,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def judge_problem(
    code_path: Path, problem_dir: Path, problem_name: str, time_limit_seconds: float
):
    input_paths = sorted(problem_dir.glob(f"{problem_name}.in.*"))
    results = []

    if not input_paths:
        raise ValueError(f"테스트 케이스를 찾을 수 없습니다: {problem_dir}")

    for input_path in input_paths:
        # print(input_path.name)

        output_name = input_path.name.replace(".in.", ".out.", 1)
        output_path = input_path.with_name(output_name)

        # print(input_path.name, "->", output_path.name)

        result = run_test_case(
            code_path=code_path,
            input_path=input_path,
            output_path=output_path,
            time_limit_seconds=time_limit_seconds,
        )
        print(input_path.name, result["status"], result["elapsed_seconds"])

        result["test_case"] = input_path.name
        results.append(result)

    passed_cases = sum(1 for result in results if result["status"] == "AC")
    total_cases = len(results)
    is_ac = passed_cases == total_cases

    if is_ac:
        overall_status = "AC"
    else:
        first_failure = next(result for result in results if result["status"] != "AC")
        overall_status = first_failure["status"]

    max_case_seconds = max(result["elapsed_seconds"] for result in results)

    return {
        "status": overall_status,
        "passed_cases": passed_cases,
        "total_cases": total_cases,
        "max_case_seconds": max_case_seconds,
        "time_limit_seconds": time_limit_seconds,
        "test_results": results,
    }


if __name__ == "__main__":
    # result = run_test_case(
    #     code_path=Path("tmp/ac.py"),
    #     # code_path=Path("tmp/wa.py"),
    #     # code_path=Path("tmp/re.py"),
    #     # code_path=Path("tmp/tle.py"),
    #     input_path=Path("data/coci/2025_2026/contest5/testdata/skare/skare.in.1a"),
    #     output_path=Path("data/coci/2025_2026/contest5/testdata/skare/skare.out.1a"),
    #     time_limit_seconds=3.0,
    # )

    # print(result)

    judge_result = judge_problem(
        code_path=Path("tmp/skare_correct.py"),
        problem_dir=Path("data/coci/2025_2026/contest5/testdata/skare"),
        problem_name="skare",
        time_limit_seconds=3.0,
    )

    print("최종 판정:", judge_result["status"])
    print(
        "통과:",
        judge_result["passed_cases"],
        "/",
        judge_result["total_cases"],
    )
    print("최대 실행 시간:", judge_result["max_case_seconds"])
