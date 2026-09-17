import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from llm_eval.local import metrics as runtime
from llm_eval.local import server
from llm_eval.local import runner, warmup
from llm_eval.local.client import chat


class WarmupTests(unittest.TestCase):
    @patch("llm_eval.local.warmup.chat")
    def test_repeated_warmup_creates_no_files(self, call):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                with contextlib.redirect_stdout(io.StringIO()):
                    warmup.run_warmup("qwen36", Mock())
                    warmup.run_warmup("qwen36", Mock())
                self.assertEqual(list(Path(tmp).iterdir()), [])
                self.assertEqual(call.call_count, 2)
                self.assertEqual(call.call_args.kwargs["max_tokens"], 128)
            finally:
                os.chdir(previous)

    @patch("llm_eval.local.warmup.chat", side_effect=RuntimeError("offline"))
    def test_warmup_failure_propagates(self, _):
        with self.assertRaisesRegex(RuntimeError, "offline"):
            warmup.run_warmup("qwen36", Mock())
