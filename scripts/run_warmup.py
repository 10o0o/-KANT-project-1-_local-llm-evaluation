import argparse
from pathlib import Path

from llm_eval.benchmark.warmup import run_warmup
from llm_eval.llama_cpp import create_client
from llm_eval.runtime import load_environment


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run one warmup request for a local LLM."
    )

    parser.add_argument(
        "--model",
        required=True,
        choices=["qwen36", "gemma4"],
    )

    parser.add_argument(
        "--environment",
        required=True,
        type=Path,
        help="Environment JSON from start_model.py",
    )

    return parser.parse_args()


def main(project_root: Path):
    args = parse_args()
    environment = load_environment(args.environment, args.model, project_root)

    with create_client() as client:
        run_warmup(
            project_root=project_root,
            model=args.model,
            client=client,
            environment=environment,
        )


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1])
