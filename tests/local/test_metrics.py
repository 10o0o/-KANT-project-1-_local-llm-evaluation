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

    @patch("llm_eval.local.metrics.command_output")
    def test_process_memory_does_not_fall_back_to_device(self, command):
        for value in ("[N/A]", "-1", "nan"):
            command.side_effect = ["GPU-1, Test, 4000, 8000", f"123, GPU-1, {value}"]
            result = runtime.observe_memory(123, "response_received")
            self.assertEqual(result["devices"]["value"][0]["used_mib"], 4000)
            self.assertIsNone(result["process"]["value"])

    @patch("llm_eval.local.metrics.command_output")
    def test_process_memory_matches_only_server(self, command):
        command.side_effect = [
            "GPU-1, Test, 4000, 8000",
            "123, GPU-1, 512\n999, GPU-1, 2048",
        ]
        self.assertEqual(
            runtime.observe_memory(123, "response_received")["process"]["value"], 512
        )

    @patch("llm_eval.local.metrics.observe_memory", return_value={"snapshot": True})
    @patch("llm_eval.local.metrics.find_server_pid", return_value=123)
    def test_automatic_pid_lookup(self, find, observe):
        self.assertEqual(
            runtime.safe_memory(None, "response_received", model="qwen36"),
            {"snapshot": True},
        )
        find.assert_called_once_with("qwen36")
        observe.assert_called_once_with(123, "response_received")

    @patch("llm_eval.local.metrics.observe_memory", side_effect=RuntimeError("unavailable"))
    def test_observation_failure_is_data(self, _):
        self.assertIsNone(runtime.safe_memory(123, "call_error")["process"]["value"])

    @patch("llm_eval.local.server.owns_server_port", return_value=True)
    @patch("llm_eval.local.server.Path")
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
        self.assertEqual(server.find_server_pid("qwen36"), 123)
        path.return_value.iterdir.return_value = [
            process(123, "qwen36"),
            process(456, "qwen36"),
        ]
        self.assertIsNone(server.find_server_pid("qwen36"))
