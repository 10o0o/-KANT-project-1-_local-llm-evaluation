"""Chat Completions provider: one record shape, a separate result tree, no invented price."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.cloud import client
from llm_eval.cloud import generation as runner
from llm_eval.shared.artifacts import validate_artifacts
from llm_eval.shared.problems import build_problem_prompt

from .helpers import chat_usage

MOTIF = client.PROVIDERS["motif3"]


class MotifRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "statement.md").write_text("same statement", encoding="utf-8")
        self.problem = {
            "id": "test_id", "name": "test_problem", "title": "Test", "difficulty": 1,
            "statement_path": "statement.md", "problem_dir": "testdata",
            "time_limit_seconds": 1, "memory_limit_mib": 512,
        }
        self.output = self.root / "results/benchmark/test_problem/motif3/round_1"
        self.sdk = Mock()
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)

    def response(self, content="```python\nprint(1)\n```", finish_reason="stop", choices=None):
        response = Mock()
        response.model_dump.return_value = {
            "id": "chatcmpl_test",
            "object": "chat.completion",
            "model": MOTIF.model,
            "choices": [{"index": 0, "finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": content}}]
            if choices is None else choices,
            "usage": chat_usage(),
        }
        self.sdk.chat.completions.create.return_value = response
        return response

    def run_problem(self, round_number=1):
        return runner.run_problem(
            self.root, self.problem, self.sdk, provider=MOTIF, round_number=round_number
        )

    def record(self, round_number=1):
        output = self.root / f"results/benchmark/test_problem/motif3/round_{round_number}"
        return json.loads((output / "result.json").read_text())

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_chat_request_is_minimal_and_saved_under_its_own_model_folder(self, judge):
        response = self.response()
        self.run_problem()
        self.assertEqual(self.sdk.chat.completions.create.call_args.kwargs, {
            "model": "motif/motif-3",
            "messages": [{"role": "user", "content": build_problem_prompt(
                "same statement", time_limit_seconds=1, memory_limit_mib=512)}],
        })
        self.sdk.responses.create.assert_not_called()
        record = self.record()
        self.assertEqual(record["model"], {
            "id": "motif/motif-3", "name": "motif3",
            "runtime": "openai_chat_completions", "response_model": "motif/motif-3",
        })
        self.assertEqual(record["call"]["status"], "success")
        self.assertEqual(record["generation"]["finish_reason"], "stop")
        self.assertIsNone(record["judge"])
        self.assertTrue(record["record_complete"])
        self.assertEqual((self.output / "candidate.py").read_text(), "print(1)")
        self.assertEqual(json.loads((self.output / "response.json").read_text()),
                         response.model_dump.return_value)
        # A second invocation must not repeat a paid request.
        self.run_problem()
        self.sdk.chat.completions.create.assert_called_once()
        judge.assert_not_called()

    def test_saved_record_passes_artifact_validation(self):
        self.response()
        self.run_problem()
        validate_artifacts(self.output, self.record())
        raw = self.output / "response.json"
        original = raw.read_bytes()
        damaged = json.loads(original)
        damaged["id"] = "chatcmpl_other"
        raw.write_text(json.dumps(damaged))
        with self.assertRaises(ValueError):
            validate_artifacts(self.output, self.record())
        raw.write_bytes(original)

    def test_usage_is_stored_raw_and_read_through_chat_field_names(self):
        self.response()
        self.run_problem()
        record = self.record()
        self.assertEqual(record["generation"]["usage"], chat_usage())
        self.assertEqual(record["metrics"]["prompt_tokens"], 1000)
        self.assertEqual(record["metrics"]["completion_tokens"], 500)
        self.assertEqual(record["metrics"]["cached_input_tokens"], 200)
        # A chat completion exposes neither reasoning nor cache-write counts.
        self.assertIsNone(record["metrics"]["reasoning_tokens"])
        self.assertTrue(record["metrics"]["reasoning_tokens_reason"])
        self.assertIsNone(record["metrics"]["cache_write_tokens"])

    def test_cost_is_not_estimated_without_a_verified_rate_table(self):
        self.response()
        self.run_problem()
        cost = self.record()["metrics"]["cost"]
        self.assertIsNone(cost["estimated_usd"])
        self.assertIn("motif/motif-3", cost["reason"])
        self.assertIsNone(cost["rates_per_million_tokens"])
        self.assertIsNone(cost["source"])
        self.assertEqual(cost["kind"], "estimate_not_invoice")

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_length_finish_reason_is_incomplete_and_still_saved(self, judge):
        self.response(finish_reason="length")
        self.run_problem()
        record = self.record()
        self.assertEqual(record["call"]["status"], "success")
        self.assertEqual(record["generation"]["status"], "incomplete")
        self.assertEqual(record["generation"]["incomplete_details"],
                         {"reason": "max_output_tokens"})
        self.assertEqual((self.output / "candidate.py").read_text(), "print(1)")
        judge.assert_not_called()

    def test_empty_or_filtered_choices_record_an_error_and_allow_resume(self):
        for choices, reason in ((None, "content_filter"), ([], None)):
            with self.subTest(choices=choices):
                self.setUp()
                if choices is None:
                    self.response("", finish_reason=reason)
                else:
                    self.response(choices=choices)
                with self.assertRaises(SystemExit):
                    self.run_problem()
                record = self.record()
                # A malformed reply is a recorded failure, never a crashed post-processing
                # step that would leave the reserved folder unusable.
                self.assertNotIn("processing_error", record)
                self.assertTrue(record["record_complete"])
                self.assertEqual(record["call"],
                                 {"status": "error", "error": {"type": "ResponseNotCompleted"}})
                self.assertFalse((self.output / "candidate.py").exists())
                self.run_problem()
                self.sdk.chat.completions.create.assert_called_once()

    def test_transport_failure_is_recorded_without_leaking_the_message(self):
        secret = "sensitive-placeholder-must-not-be-saved"
        self.sdk.chat.completions.create.side_effect = RuntimeError(secret)
        with self.assertRaises(SystemExit) as raised:
            self.run_problem()
        record = self.record()
        self.assertEqual(record["call"]["error"], {"type": "RuntimeError", "status_code": None})
        self.assertNotIn(secret, (self.output / "result.json").read_text())
        self.assertNotIn(secret, str(raised.exception))
        self.run_problem()
        self.sdk.chat.completions.create.assert_called_once()

    def test_changed_prompt_aborts_without_a_second_call(self):
        self.response("No code")
        self.run_problem()
        (self.root / "statement.md").write_text("changed statement")
        with self.assertRaisesRegex(SystemExit, "현재 입력"):
            self.run_problem()
        self.sdk.chat.completions.create.assert_called_once()

    def test_rounds_and_providers_keep_separate_result_trees(self):
        self.response()
        self.run_problem(round_number=1)
        self.run_problem(round_number=2)
        luna = Mock()
        luna_response = Mock()
        luna_response.output_text = "no code"
        luna_response.model_dump.return_value = {
            "id": "resp_test", "model": client.LUNA.model, "status": "completed",
            "service_tier": "default", "usage": None,
        }
        luna.responses.create.return_value = luna_response
        runner.run_problem(self.root, self.problem, luna, provider=client.LUNA)
        for relative in ("motif3/round_1", "motif3/round_2", "luna/round_1"):
            with self.subTest(relative=relative):
                path = self.root / "results/benchmark/test_problem" / relative
                self.assertTrue((path / "result.json").exists())
        self.assertEqual(self.record(1)["experiment"]["round"], 1)
        self.assertEqual(self.record(2)["experiment"]["round"], 2)
