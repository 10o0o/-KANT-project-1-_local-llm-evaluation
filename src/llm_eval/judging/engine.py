import sys
import time
from pathlib import Path

from llm_eval.judging.process import (
    ProcessCleanupError,
    collect_bounded_output,
    spawn_isolated,
)


OUTPUT_LIMIT_BYTES = 10 * 1024 * 1024
JUDGE_POLICY = {
    "version": 1,
    "per_test_output_limit_bytes": OUTPUT_LIMIT_BYTES,
    "output_limit_scope": "combined_stdout_stderr_bytes",
    "resource_verdict_precedence": "first_trigger",
}


def run_test_case(
    code_path: Path, input_path: Path, output_path: Path, time_limit_seconds: float
):
    with open(output_path, "r", encoding="utf-8") as f:
        expected_output = f.read()

    # print("INPUT:")
    # print(input_text)

    # print("EXPECTED:")
    # print(expected_output)

    with open(input_path, "rb") as input_stream:
        started_at = time.monotonic()
        process = spawn_isolated(
            [sys.executable, str(code_path)],
            stdin=input_stream,
        )
        completed = collect_bounded_output(
            process,
            timeout_seconds=time_limit_seconds,
            output_limit_bytes=OUTPUT_LIMIT_BYTES,
            started_at=started_at,
        )

    if not completed.pipes_drained:
        raise ProcessCleanupError("candidate pipes did not reach EOF after cleanup")

    resource_verdict = {
        "timeout": "TLE",
        "output_limit": "OLE",
    }.get(completed.termination_reason)
    decode_errors = "replace" if resource_verdict is not None else "strict"
    stdout = completed.stdout.decode("utf-8", errors=decode_errors)
    stderr = completed.stderr.decode("utf-8", errors=decode_errors)

    # print("실행 결과:", completed.stdout)
    # print("정답:", expected_output)
    # print("return code:", completed.returncode)
    # print("실행 시간:", elapsed)

    actual_tokens = stdout.split()
    expected_tokens = expected_output.split()

    # if actual_tokens == expected_tokens:
    #     status = "AC"
    # else:
    #     status = "WA"

    if resource_verdict is not None:
        status = resource_verdict
    elif completed.returncode != 0:
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
        "elapsed_seconds": completed.elapsed_seconds,
        "return_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": completed.timed_out,
        "output_limit_exceeded": completed.output_limit_exceeded,
        "pipes_drained": completed.pipes_drained,
        "termination_reason": completed.termination_reason,
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
