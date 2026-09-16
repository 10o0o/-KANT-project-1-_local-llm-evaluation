import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from llm_eval import runtime
from llm_eval.benchmark import runner, warmup
from llm_eval.llama_cpp import chat


class RuntimeTests(unittest.TestCase):
    def test_request_disables_prompt_cache(self):
        client = Mock()
        chat(client, "qwen36", "example")
        self.assertIs(
            client.chat.completions.create.call_args.kwargs["extra_body"][
                "cache_prompt"
            ],
            False,
        )

    def test_metrics_missing_invalid_and_zero(self):
        for timings in (
            {},
            {"predicted_ms": 0, "predicted_per_second": 10},
            {"predicted_ms": 1, "predicted_per_second": float("nan")},
        ):
            result = runtime.measured_metrics(2, {}, timings, {})
            self.assertIsNone(result["generation_tokens_per_second"])
            self.assertTrue(result["generation_tokens_per_second_reason"])
        result = runtime.measured_metrics(
            2,
            {"completion_tokens": 0},
            {"predicted_ms": 1, "predicted_per_second": 0},
            {},
        )
        self.assertEqual(result["generation_tokens_per_second"], 0)
        self.assertEqual(result["completion_tokens"], 0)
        self.assertIsNone(result["model_load_seconds"])

    @patch("llm_eval.runtime.command_output")
    def test_process_memory_does_not_fall_back_to_device(self, command):
        for value in ("[N/A]", "-1", "nan"):
            command.side_effect = ["GPU-1, Test, 4000, 8000", f"123, GPU-1, {value}"]
            result = runtime.observe_memory(123, "response_received")
            self.assertEqual(result["devices"]["value"][0]["used_mib"], 4000)
            self.assertIsNone(result["process"]["value"])

    @patch("llm_eval.runtime.command_output")
    def test_process_memory_matches_only_server(self, command):
        command.side_effect = [
            "GPU-1, Test, 4000, 8000",
            "123, GPU-1, 512\n999, GPU-1, 2048",
        ]
        self.assertEqual(
            runtime.observe_memory(123, "response_received")["process"]["value"], 512
        )

    @patch("llm_eval.runtime.observe_memory", return_value={"snapshot": True})
    @patch("llm_eval.runtime.find_server_pid", return_value=123)
    def test_automatic_pid_lookup(self, find, observe):
        self.assertEqual(
            runtime.safe_memory(None, "response_received", model="qwen36"),
            {"snapshot": True},
        )
        find.assert_called_once_with("qwen36")
        observe.assert_called_once_with(123, "response_received")

    @patch("llm_eval.runtime.observe_memory", side_effect=RuntimeError("unavailable"))
    def test_observation_failure_is_data(self, _):
        self.assertIsNone(runtime.safe_memory(123, "call_error")["process"]["value"])

    @patch("llm_eval.runtime.owns_server_port", return_value=True)
    @patch("llm_eval.runtime.Path")
    def test_server_discovery_matches_alias_and_rejects_ambiguity(self, path, owns):
        def process(pid, alias):
            proc = MagicMock()
            proc.name = str(pid)
            exe = Mock()
            exe.resolve.return_value.name = "llama-server"
            cmdline = Mock()
            cmdline.read_bytes.return_value = (
                f"llama-server\0--alias\0{alias}\0".encode()
            )
            proc.__truediv__.side_effect = {"exe": exe, "cmdline": cmdline}.__getitem__
            return proc

        path.return_value.iterdir.return_value = [
            process(123, "qwen36"),
            process(456, "gemma4"),
        ]
        self.assertEqual(runtime.find_server_pid("qwen36"), 123)
        path.return_value.iterdir.return_value = [
            process(123, "qwen36"),
            process(456, "qwen36"),
        ]
        self.assertIsNone(runtime.find_server_pid("qwen36"))


class WarmupTests(unittest.TestCase):
    @patch("llm_eval.benchmark.warmup.chat")
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

    @patch("llm_eval.benchmark.warmup.chat", side_effect=RuntimeError("offline"))
    def test_warmup_failure_propagates(self, _):
        with self.assertRaisesRegex(RuntimeError, "offline"):
            warmup.run_warmup("qwen36", Mock())


class BenchmarkTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
