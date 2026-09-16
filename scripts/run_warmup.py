import argparse

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


def main():
    args = parse_args()

    with create_client() as client:
        run_warmup(
            model=args.model,
            client=client,
        )


if __name__ == "__main__":
    main()
