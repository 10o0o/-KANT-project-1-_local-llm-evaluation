import argparse
from pathlib import Path

from llm_eval.benchmark.runner import run_problem
from llm_eval.llama_cpp import create_client
from llm_eval.problems import load_problems, select_problems


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

    # Both rounds independently use the same prompt and generation settings.
    parser.add_argument(
        "--round",
        required=True,
        type=int,
        choices=[1, 2],
        help="Independent repeat number (1 or 2); no previous answer is used.",
    )

    return parser.parse_args()



def main(project_root: Path):
    args = parse_args()
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
