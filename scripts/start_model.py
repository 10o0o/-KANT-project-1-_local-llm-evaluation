import argparse
from pathlib import Path

from llm_eval.server_session import start_model


def main():
    parser = argparse.ArgumentParser(
        description="Start a local server and record its runtime session."
    )
    parser.add_argument("--model", required=True, choices=["qwen36", "gemma4"])
    parser.add_argument(
        "--ready-timeout",
        type=float,
        default=600,
        help="Readiness deadline in seconds (default: 600).",
    )
    args = parser.parse_args()
    return start_model(
        Path(__file__).resolve().parents[1], args.model, args.ready_timeout
    )


if __name__ == "__main__":
    raise SystemExit(main())
