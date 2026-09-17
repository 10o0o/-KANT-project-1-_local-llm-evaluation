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
from llm_eval.local import generation as runner
from llm_eval.local.client import chat


class BenchmarkTests(unittest.TestCase):
    def test_postprocessing_failure_is_recorded_and_never_recalled(self):
        problem = dict(id="p", name="p", title="P", difficulty=1,
                       time_limit_seconds=1, memory_limit_mib=512,
                       judge_type="token", statement_path="statement.md")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "statement.md").write_text("Example")
            response = Mock()
            response.model_dump.return_value = {"choices": []}
            with patch.object(runner, "chat", return_value=response) as call, \
                 patch.object(runner, "safe_memory", return_value={}), \
                 patch.object(runner, "perf_counter", side_effect=[10, 12]), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(IndexError):
                    runner.run_problem(root, problem, "qwen36", 1, Mock())
                path = root / "results/benchmark/p/qwen36/round_1/result.json"
                self.assertTrue(path.exists(), "postprocessing error must leave a record")
                record = json.loads(path.read_text())
                self.assertFalse(record["record_complete"])
                self.assertEqual(record["processing_error"]["stage"], "extract_response")
                self.assertEqual(record["metrics"]["response_elapsed_seconds"], 2)
                self.assertTrue(record["run_id"].endswith("Z"))
                with self.assertRaises(SystemExit):
                    runner.run_problem(root, problem, "qwen36", 1, Mock())
                call.assert_called_once()

    def test_atomic_storage_failure_records_stage_and_preserves_raw(self):
        problem = dict(id="p", name="p", title="P", difficulty=1,
                       time_limit_seconds=1, memory_limit_mib=512,
                       judge_type="token", statement_path="statement.md")
        for failed_file, expected_stage in (("response.json", "save_response"),
                                            ("candidate.py", "save_candidate"),
                                            ("result.json", "save_record")):
            with self.subTest(file=failed_file), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "statement.md").write_text("Example")
                response = Mock()
                response.model_dump.return_value = {"choices": [{"finish_reason": "stop",
                    "message": {"content": "```python\nprint(1)\n```"}}]}
                replace = Path.replace
                failed_once = False
                def fail_once(path, target):
                    nonlocal failed_once
                    if Path(target).name == failed_file and not failed_once:
                        failed_once = True
                        raise OSError("mock disk failure")
                    return replace(path, target)
                with patch.object(runner, "chat", return_value=response) as call, \
                     patch.object(runner, "safe_memory", return_value={}), \
                     patch.object(Path, "replace", fail_once), \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(OSError):
                        runner.run_problem(root, problem, "qwen36", 1, Mock())
                    path = root / "results/benchmark/p/qwen36/round_1/result.json"
                    record = json.loads(path.read_text())
                    self.assertFalse(record["record_complete"])
                    self.assertEqual(record["processing_error"]["stage"], expected_stage)
                    self.assertFalse(list(path.parent.glob("*.tmp")))
                    if failed_file != "response.json":
                        self.assertEqual(json.loads(path.with_name("response.json").read_text()),
                                         response.model_dump.return_value)
                    with self.assertRaises(SystemExit):
                        runner.run_problem(root, problem, "qwen36", 1, Mock())
                    call.assert_called_once()

    def test_success_and_failure_records_without_environment(self):
        problem = {
            "id": "p",
            "name": "p",
            "title": "P",
            "difficulty": 1,
            "time_limit_seconds": 1,
            "memory_limit_mib": 512,
            "judge_type": "token",
            "problem_dir": "tests",
            "statement_path": "statement.md",
        }
        response = Mock()
        response.model_dump.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": "No code"}}],
            "usage": {},
            "timings": {"predicted_ms": 1, "predicted_per_second": 10},
        }
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "statement.md").write_text("Example")
                with (
                    patch.object(
                        runner,
                        "chat",
                        side_effect=RuntimeError("offline") if failed else None,
                        return_value=response,
                    ),
                    patch.object(
                        runner,
                        "safe_memory",
                        return_value={
                            "process": {"value": None, "reason": "unsupported"}
                        },
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    if failed:
                        with self.assertRaisesRegex(RuntimeError, "offline"):
                            runner.run_problem(root, problem, "qwen36", 1, Mock())
                    else:
                        runner.run_problem(root, problem, "qwen36", 1, Mock())
                path = next(root.glob("results/**/result.json"))
                record = json.loads(path.read_text())
                self.assertNotIn("environment", record)
                self.assertEqual(
                    record["call"]["status"], "error" if failed else "success"
                )
                self.assertIs(record["generation_config"]["cache_prompt"], False)
                self.assertIn("memory", record["metrics"])
                self.assertIn("request", record)
                self.assertIn("judge", record)
                if not failed:
                    self.assertTrue(path.with_name("response.json").exists())
                    self.assertEqual(
                        record["metrics"]["generation_tokens_per_second"], 10
                    )
