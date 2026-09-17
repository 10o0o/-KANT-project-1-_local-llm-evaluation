"""Compatibility entrypoint; prefer run_local_benchmark.py."""
from pathlib import Path
import runpy

def main():
    runpy.run_path(str(Path(__file__).with_name("run_local_benchmark.py")), run_name="__main__")

if __name__ == "__main__":
    main()
