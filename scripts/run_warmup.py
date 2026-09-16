import argparse
from pathlib import Path

from llm_eval.benchmark.warmup import run_warmup
from llm_eval.llama_cpp import create_client


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


def main(project_root: Path):
    args = parse_args()

    with create_client() as client:
        run_warmup(
            project_root=project_root,
            model=args.model,
            client=client,
        )


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1])
