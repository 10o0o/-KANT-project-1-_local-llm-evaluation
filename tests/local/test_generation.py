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


class DemoTests(unittest.TestCase):
    @staticmethod
    def problem():
        return {
            "id": "p",
            "name": "p",
            "title": "P",
            "difficulty": 1,
            "time_limit_seconds": 1,
            "memory_limit_mib": 512,
            "judge_type": "token",
            "statement_path": "statement.md",
        }

    @staticmethod
    def response(content="```python\nprint(1)\n```"):
        response = Mock()
        response.model_dump.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": content},
            }],
        }
        return response

    def prepare(self, root):
        (root / "statement.md").write_text("Example")

    def test_none_round_writes_demo_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            response = self.response()
            with patch.object(runner, "chat", return_value=response), \
                 patch.object(runner, "safe_memory", return_value={}), \
                 contextlib.redirect_stdout(io.StringIO()):
                runner.run_problem(root, self.problem(), "qwen36", None, Mock())

            path = root / "results/demo/p/qwen36/result.json"
            self.assertTrue(path.exists())
            self.assertEqual(
                json.loads(path.read_text())["experiment"],
                {"type": "demo", "round": None},
            )

    def test_demo_rerun_success_uses_fresh_call_and_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            first_response = self.response("```python\nprint(1)\n```")
            second_response = self.response("```python\nprint(2)\n```")
            with patch.object(
                runner, "chat", side_effect=[first_response, second_response]
            ) as call, patch.object(runner, "safe_memory", return_value={}), \
                    contextlib.redirect_stdout(io.StringIO()):
                runner.run_problem(root, self.problem(), "qwen36", None, Mock())
                first = json.loads(
                    (root / "results/demo/p/qwen36/result.json").read_text()
                )
                runner.run_problem(root, self.problem(), "qwen36", None, Mock())
                second = json.loads(
                    (root / "results/demo/p/qwen36/result.json").read_text()
                )

            self.assertEqual(call.call_count, 2)
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertEqual(
                (root / "results/demo/p/qwen36/candidate.py").read_text(),
                "print(2)",
            )
            self.assertFalse((root / "results/benchmark").exists())

    def test_demo_rerun_replaces_success_with_no_code_or_call_error(self):
        for outcome in ("no_code", "call_error"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root)
                first_response = self.response()
                replacement = (
                    self.response("No code")
                    if outcome == "no_code"
                    else RuntimeError("offline")
                )
                with patch.object(
                    runner, "chat", side_effect=[first_response, replacement]
                ) as call, patch.object(runner, "safe_memory", return_value={}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    runner.run_problem(root, self.problem(), "qwen36", None, Mock())
                    demo = root / "results/demo/p/qwen36"
                    (demo / "unrelated.txt").write_text("keep me")
                    if outcome == "call_error":
                        with self.assertRaises(RuntimeError):
                            runner.run_problem(
                                root, self.problem(), "qwen36", None, Mock()
                            )
                    else:
                        runner.run_problem(root, self.problem(), "qwen36", None, Mock())

                record = json.loads((demo / "result.json").read_text())
                self.assertEqual(call.call_count, 2)
                self.assertEqual((demo / "unrelated.txt").read_text(), "keep me")
                self.assertFalse((demo / "candidate.py").exists())
                if outcome == "no_code":
                    self.assertEqual(record["call"]["status"], "success")
                    self.assertIsNone(record["extracted_code"])
                    self.assertTrue((demo / "response.json").exists())
                else:
                    self.assertEqual(record["call"]["status"], "error")
                    self.assertFalse((demo / "response.json").exists())

    def test_partial_or_corrupt_demo_is_replaced(self):
        for state in ("partial", "corrupt"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root)
                demo = root / "results/demo/p/qwen36"
                demo.mkdir(parents=True)
                (demo / "unrelated.txt").write_text("keep me")
                if state == "corrupt":
                    (demo / "result.json").write_text("not json")
                response = self.response()
                with patch.object(runner, "chat", return_value=response), \
                        patch.object(runner, "safe_memory", return_value={}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    runner.run_problem(root, self.problem(), "qwen36", None, Mock())

                self.assertTrue((demo / "result.json").exists())
                self.assertEqual((demo / "unrelated.txt").read_text(), "keep me")
                self.assertTrue((demo / "candidate.py").exists())

    def test_demo_replacement_preserves_other_models_and_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            other = root / "results/demo/p/gemma4/keep.txt"
            other.parent.mkdir(parents=True)
            other.write_bytes(b"other model")
            benchmark = root / "results/benchmark/p/qwen36/round_1/result.json"
            benchmark.parent.mkdir(parents=True)
            benchmark.write_bytes(b"benchmark")
            target = root / "results/demo/p/qwen36"
            target.mkdir(parents=True)
            (target / "unrelated.txt").write_text("keep me")

            with patch.object(runner, "chat", return_value=self.response()), \
                    patch.object(runner, "safe_memory", return_value={}), \
                    contextlib.redirect_stdout(io.StringIO()):
                runner.run_problem(root, self.problem(), "qwen36", None, Mock())

            self.assertEqual(other.read_bytes(), b"other model")
            self.assertEqual(benchmark.read_bytes(), b"benchmark")
            self.assertEqual((target / "unrelated.txt").read_text(), "keep me")


class SelectionTests(unittest.TestCase):
    def test_omitted_round_is_forwarded_as_demo_sentinel(self):
        root = Path("/fixture")
        problem = {"id": "p1"}
        client = Mock()
        client_context = Mock()
        client_context.__enter__ = Mock(return_value=client)
        client_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(runner, "load_problems", return_value=[problem]),
            patch.object(runner, "select_problems", return_value=[problem]),
            patch.object(runner, "workload", return_value=contextlib.nullcontext()),
            patch.object(runner, "create_client", return_value=client_context),
            patch.object(runner, "run_problem") as run_problem,
        ):
            runner.run_selected(root, "qwen36", "p1")

        run_problem.assert_called_once_with(root, problem, "qwen36", None, client)
