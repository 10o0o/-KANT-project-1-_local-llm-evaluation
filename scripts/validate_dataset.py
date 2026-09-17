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


def main():
    root = Path(__file__).resolve().parents[1]
    problems_path = root / "data/coci/problems.json"

    problems = json.loads(problems_path.read_text(encoding="utf-8"))

    errors = []

    if len(problems) != EXPECTED_PROBLEM_COUNT:
        errors.append(
            f"problem count: expected {EXPECTED_PROBLEM_COUNT}, got {len(problems)}"
        )

    ids = [p.get("id") for p in problems]
    names = [p.get("name") for p in problems]

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

        statement_path = root / problem["statement_path"]
        problem_dir = root / problem["problem_dir"]

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

        valid = len(errors) == errors_before and ids.count(problem_id) == 1 and names.count(name) == 1
        label = "OK" if valid else "ERROR"
        print(
            f"[{label}] {problem_id:<35} "
            f"tests={len(input_files):>3} "
            f"difficulty={problem['difficulty']}"
        )

    print()
    print(f"Problems: {len(problems)}")

    if errors:
        print("\nValidation FAILED")

        for error in errors:
            print(f"- {error}")

        raise SystemExit(1)

    print("Validation PASSED")


if __name__ == "__main__":
    main()
