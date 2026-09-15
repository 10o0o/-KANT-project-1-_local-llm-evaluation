from pathlib import Path

from llm_eval.benchmark.cli import main


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1])
