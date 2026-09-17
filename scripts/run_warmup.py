import argparse
from pathlib import Path

from llm_eval.local.warmup import run_warmup
from llm_eval.local.client import create_client
from llm_eval.shared.processes import workload


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run one warmup request for a local LLM."
    )

    parser.add_argument(
        "--model",
        required=True,
        choices=["qwen36", "gemma4"],
    )

    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]

    with workload(project_root, "warmup", allow_inherited=True):
        with create_client() as client:
            run_warmup(
                model=args.model,
                client=client,
            )


if __name__ == "__main__":
    main()
