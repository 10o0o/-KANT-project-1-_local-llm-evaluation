import contextlib
import fcntl
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_eval.judging import batch
from llm_eval.shared.storage import write_json


class StorageTests(unittest.TestCase):

    def test_atomic_write_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            write_json(path, {"original": True})
            with patch("llm_eval.shared.storage.os.fsync", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    write_json(path, {"original": False})
            self.assertEqual(json.loads(path.read_text()), {"original": True})
            self.assertEqual(list(path.parent.iterdir()), [path])
