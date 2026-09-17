import argparse

from llm_eval.cloud.client import create_client
from llm_eval.cloud.runner import run_problem
from llm_eval.shared.problems import load_problems, select_problems
from llm_eval.shared.processes import workload


def main(project_root):
    parser = argparse.ArgumentParser(
        description=(
            "Run the selected independent Luna repeat without using a previous answer."
        )
    )
    parser.add_argument("--problems", required=True, help="Comma-separated problem IDs, or all")
    parser.add_argument(
        "--round", type=int, choices=(1, 2), default=1,
        help="Independent repeat to run; neither round uses the previous answer",
    )
    args = parser.parse_args()
    with workload(project_root, "cloud"):
        selected = select_problems(load_problems(project_root), args.problems)
        if len({p["id"] for p in selected}) != len(selected):
            raise SystemExit("중복 문제 ID는 허용하지 않습니다.")
        with create_client() as client:
            for problem in selected:
                run_problem(
                    project_root,
                    problem,
                    client,
                    [p["id"] for p in selected],
                    round_number=args.round,
                )
