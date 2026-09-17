import json
from pathlib import Path


EXPECTED_PROBLEM_COUNT = 10
REQUIRED_FIELDS = {
    "id",
    "name",
    "season",
    "contest",
    "difficulty",
    "difficulty_reason",
    "problem_dir",
    "statement_path",
    "time_limit_seconds",
    "memory_limit_mib",
    "judge_type",
    "title",
}


def load_problems(project_root: Path) -> list[dict]:
    problems_path = project_root / "data" / "coci" / "problems.json"

    with open(problems_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_problem(problems: list[dict], problem_id: str) -> dict:
    for problem in problems:
        if problem["id"] == problem_id:
            return problem

    raise ValueError(f"문제를 찾을 수 없습니다: {problem_id}")


def select_problems(problems: list[dict], selection: str) -> list[dict]:
    selection = selection.strip()

    if selection == "all":
        return problems

    problem_ids = [problem_id.strip() for problem_id in selection.split(",")]

    return [get_problem(problems, problem_id) for problem_id in problem_ids]


def build_problem_prompt(
    statement: str, *, time_limit_seconds: float, memory_limit_mib: int
) -> str:
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

실행 제한:
- 시간 제한: {time_limit_seconds:g}초
- 메모리 제한: {memory_limit_mib} MiB

문제:

{statement}
""".strip()


def problem_prompt(project_root: Path, problem: dict) -> str:
    statement = (project_root / problem["statement_path"]).read_text(encoding="utf-8")
    return build_problem_prompt(
        statement,
        time_limit_seconds=problem["time_limit_seconds"],
        memory_limit_mib=problem["memory_limit_mib"],
    )


def validate_dataset(project_root: Path) -> tuple[list[str], list[str]]:
    problems = load_problems(project_root)
    messages = []
    errors = []

    if len(problems) != EXPECTED_PROBLEM_COUNT:
        errors.append(
            f"problem count: expected {EXPECTED_PROBLEM_COUNT}, got {len(problems)}"
        )

    ids = [problem.get("id") for problem in problems]
    names = [problem.get("name") for problem in problems]
    if len(ids) != len(set(ids)):
        errors.append("duplicate problem id found")
    if len(names) != len(set(names)):
        errors.append("duplicate problem name found")

    for problem in problems:
        errors_before = len(errors)
        problem_id = problem.get("id", "<unknown>")
        name = problem.get("name", "<unknown>")
        missing_fields = REQUIRED_FIELDS - problem.keys()
        if missing_fields:
            errors.append(f"{problem_id}: missing fields: {sorted(missing_fields)}")
            continue

        if not 1 <= problem["difficulty"] <= 10:
            errors.append(f"{problem_id}: invalid difficulty {problem['difficulty']}")
        if problem["judge_type"] != "token":
            errors.append(
                f"{problem_id}: unsupported judge_type={problem['judge_type']}"
            )

        statement_path = project_root / problem["statement_path"]
        problem_dir = project_root / problem["problem_dir"]
        if not statement_path.is_file():
            errors.append(f"{problem_id}: statement missing: {statement_path}")
        if not problem_dir.is_dir():
            errors.append(f"{problem_id}: testdata directory missing: {problem_dir}")
            continue

        input_files = sorted(problem_dir.glob(f"{name}.in.*"))
        if not input_files:
            errors.append(f"{problem_id}: no input test cases found")
            continue

        missing_outputs = []
        for input_path in input_files:
            suffix = input_path.name.removeprefix(f"{name}.in.")
            output_path = problem_dir / f"{name}.out.{suffix}"
            if not output_path.is_file():
                missing_outputs.append(output_path.name)
        if missing_outputs:
            errors.append(f"{problem_id}: missing outputs: {missing_outputs}")

        valid = (
            len(errors) == errors_before
            and ids.count(problem_id) == 1
            and names.count(name) == 1
        )
        label = "OK" if valid else "ERROR"
        messages.append(
            f"[{label}] {problem_id:<35} "
            f"tests={len(input_files):>3} "
            f"difficulty={problem['difficulty']}"
        )

    messages.extend(["", f"Problems: {len(problems)}"])
    return messages, errors
