import json
import os
import tempfile
from pathlib import Path


def write_bytes(path: Path, data: bytes):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_text(path: Path, text: str):
    write_bytes(path, text.encode("utf-8"))


def write_json(path: Path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2, default=str))
