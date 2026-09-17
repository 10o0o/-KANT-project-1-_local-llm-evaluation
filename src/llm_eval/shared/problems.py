import json
from pathlib import Path


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
