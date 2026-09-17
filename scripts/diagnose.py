"""Compatibility entrypoint for the response diagnostic."""
from pathlib import Path
import runpy

def main():
    runpy.run_path(str(Path(__file__).parent / "diagnostics/response_probe.py"), run_name="__main__")

if __name__ == "__main__":
    main()
