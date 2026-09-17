from pathlib import Path


def generation_dir(root: Path, problem_name: str, model: str, round_number: int) -> Path:
    return root / "results" / "benchmark" / problem_name / model / f"round_{round_number}"
