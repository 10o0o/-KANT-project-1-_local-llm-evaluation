"""Compatibility entrypoint for the generation-limit diagnostic."""
from pathlib import Path
import runpy

def main():
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "diagnostics/generation_limit_probe.py"), run_name="__main__")

if __name__ == "__main__":
    main()
