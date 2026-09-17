import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx2 as httpx
from openai import APITimeoutError, AuthenticationError

from llm_eval.shared.problems import build_problem_prompt
from llm_eval.cloud import client, generation as runner
from llm_eval.cloud.metrics import estimated_cost


from .helpers import usage

class RunnerTests(unittest.TestCase):
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
        self.output = self.root / "results/benchmark/test_problem/luna/round_1"
        self.sdk = Mock()
        self.stdout = contextlib.redirect_stdout(io.StringIO())
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)

    def response(self, content="```python\nprint(1)\n```", status="completed"):
        response = Mock()
        response.output_text = content
        response.model_dump.return_value = {
            "id": "resp_test", "model": client.LUNA.model, "status": status,
            "service_tier": "default", "usage": usage(),
            "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": content}]}],
        }
        self.sdk.responses.create.return_value = response
        return response

    def run_problem(self, round_number=1):
        return runner.run_problem(
            self.root, self.problem, self.sdk, round_number=round_number
        )

    def record(self, round_number=1):
        output = self.root / f"results/benchmark/test_problem/luna/round_{round_number}"
        return json.loads((output / "result.json").read_text())

    def test_rounds_use_same_request_in_separate_runs(self):
        self.response()
        self.run_problem(round_number=1)
        self.run_problem(round_number=2)

        first = self.record(1)
        second = self.record(2)
        self.assertEqual(first["request"], second["request"])
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["experiment"], {
            "type": "cloud", "round": 1, "planned_attempts": 20,
        })
        self.assertEqual(second["experiment"], {
            "type": "cloud", "round": 2, "planned_attempts": 20,
        })
        self.assertEqual(self.sdk.responses.create.call_count, 2)
        self.assertEqual(
            self.sdk.responses.create.call_args_list[0].kwargs,
            self.sdk.responses.create.call_args_list[1].kwargs,
        )
        self.run_problem(round_number=1)
        self.run_problem(round_number=2)
        self.assertEqual(self.sdk.responses.create.call_count, 2)

    def test_round_one_call_error_does_not_block_round_two_success(self):
        response = self.response()
        self.sdk.responses.create.side_effect = [RuntimeError("fixture"), response]

        with self.assertRaises(SystemExit):
            self.run_problem(round_number=1)
        self.run_problem(round_number=2)

        self.assertEqual(self.record(1)["call"]["status"], "error")
        self.assertEqual(self.record(2)["call"]["status"], "success")
        self.assertEqual(self.sdk.responses.create.call_count, 2)

    def test_legacy_round_one_planned_attempts_ten_skips_byte_for_byte(self):
        self.response()
        self.run_problem()
        path = self.output / "result.json"
        record = self.record()
        record["experiment"]["planned_attempts"] = 10
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        before = path.read_bytes()

        self.run_problem()

        self.assertEqual(path.read_bytes(), before)
        self.sdk.responses.create.assert_called_once()

    def test_round_two_error_skips_and_partial_or_mismatched_record_blocks(self):
        self.sdk.responses.create.side_effect = RuntimeError("fixture")
        with self.assertRaises(SystemExit):
            self.run_problem(round_number=2)
        self.run_problem(round_number=2)
        self.sdk.responses.create.assert_called_once()

        path = self.root / "results/benchmark/test_problem/luna/round_2/result.json"
        record = self.record(2)
        record["experiment"]["round"] = 1
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_problem(round_number=2)
        self.sdk.responses.create.assert_called_once()

        path.unlink()
        with self.assertRaises(SystemExit):
            self.run_problem(round_number=2)
        self.sdk.responses.create.assert_called_once()

    def test_invalid_direct_round_fails_before_read_reservation_or_request(self):
        (self.root / "statement.md").unlink()

        with self.assertRaisesRegex(ValueError, "1 또는 2"):
            self.run_problem(round_number=3)

        self.assertFalse((self.root / "results").exists())
        self.sdk.responses.create.assert_not_called()

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    @patch("llm_eval.cloud.generation.perf_counter", side_effect=[10, 12])
    def test_success_saves_generation_only_and_skips(self, clock, judge):
        response = self.response()

        self.run_problem()
        request = self.sdk.responses.create.call_args.kwargs
        self.assertEqual(request, {
            "model": "gpt-5.6-luna", "reasoning": {"effort": "max"},
            "max_output_tokens": 128000, "tools": [], "tool_choice": "none",
            "store": False, "service_tier": "default",
            "input": [{"role": "user", "content": build_problem_prompt("same statement", time_limit_seconds=1, memory_limit_mib=512)}],
        })
        record = self.record()
        self.assertIsNone(record["judge"])
        self.assertTrue(record["record_complete"])
        self.assertEqual((self.output / "candidate.py").read_text(), "print(1)")
        self.assertEqual(json.loads((self.output / "response.json").read_text()), response.model_dump.return_value)
        self.assertEqual(record["metrics"]["response_elapsed_seconds"], 2)
        self.assertIsNone(record["metrics"]["generation_tokens_per_second"])
        self.assertEqual(record["model"]["response_model"], client.LUNA.model)
        self.assertEqual(record["generation"]["response_id"], "resp_test")
        self.run_problem()
        self.sdk.responses.create.assert_called_once()
        judge.assert_not_called()
        self.assertFalse((self.root / "results/cloud").exists())

    def test_artifact_damage_aborts_without_recall(self):
        self.response()
        self.run_problem()
        candidate = self.output / "candidate.py"
        raw = self.output / "response.json"
        for path, damaged in ((candidate, "tampered"), (raw, "[]"), (raw, None)):
            original = path.read_bytes()
            if damaged is None:
                path.unlink()
            else:
                path.write_text(damaged)
            with self.subTest(path=path, damaged=damaged), self.assertRaises(SystemExit):
                self.run_problem()
            path.write_bytes(original)
        self.sdk.responses.create.assert_called_once()

    def test_failed_response_still_requires_raw_artifact(self):
        self.response("", "failed")
        with self.assertRaises(SystemExit):
            self.run_problem()
        (self.output / "response.json").unlink()
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.sdk.responses.create.assert_called_once()

    def test_changed_limits_abort_without_second_call(self):
        self.response(content="no code")
        self.run_problem()
        for field, value in (("time_limit_seconds", 2), ("memory_limit_mib", 256)):
            with self.subTest(field=field):
                original = self.problem[field]
                self.problem[field] = value
                with self.assertRaisesRegex(SystemExit, "입력·설정"):
                    self.run_problem()
                self.problem[field] = original
        self.sdk.responses.create.assert_called_once()

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_refusal_no_code_and_missing_usage(self, judge):
        response = self.response("", "completed")
        response.model_dump.return_value["usage"] = None
        response.model_dump.return_value["output"] = [{"type": "message", "content": [{"type": "refusal", "refusal": "Cannot answer"}]}]
        self.run_problem()
        record = self.record()
        self.assertIsNone(record["judge"])
        self.assertIsNone(record["metrics"]["cost"]["estimated_usd"])
        self.assertFalse((self.output / "candidate.py").exists())
        judge.assert_not_called()

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_incomplete_with_code_is_saved(self, judge):
        self.response(status="incomplete")
        self.run_problem()
        record = self.record()
        self.assertEqual(record["generation"]["status"], "incomplete")
        self.assertIsNone(record["judge"])
        judge.assert_not_called()
        self.assertEqual(record["generation"]["incomplete_details"]["reason"], "max_output_tokens")

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_incomplete_without_code(self, judge):
        self.response("unfinished answer", "incomplete")
        self.run_problem()
        self.assertIsNone(self.record()["judge"])
        judge.assert_not_called()

    def test_api_failure_safe_record_and_skip(self):
        secret = "sensitive-placeholder-must-not-be-saved"
        error = AuthenticationError(secret, response=httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/responses")), body={"detail": secret})
        self.sdk.responses.create.side_effect = error
        with self.assertRaises(SystemExit) as raised:
            self.run_problem()
        record = self.record()
        self.assertEqual(record["call"]["error"], {"type": "AuthenticationError", "status_code": 401})
        self.assertNotIn(secret, (self.output / "result.json").read_text())
        self.assertNotIn(secret, str(raised.exception))
        self.assertIsNone(record["metrics"]["cost"]["estimated_usd"])
        self.run_problem()
        self.sdk.responses.create.assert_called_once()

    def test_timeout_is_recorded(self):
        self.sdk.responses.create.side_effect = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.assertEqual(self.record()["call"]["error"]["type"], "APITimeoutError")

    def test_incomplete_folder_blocks_before_request(self):
        self.output.mkdir(parents=True)
        (self.output / "response.json").write_text("original")
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.sdk.responses.create.assert_not_called()
        self.assertEqual((self.output / "response.json").read_text(), "original")

    def test_malformed_result_blocks_before_request(self):
        self.output.mkdir(parents=True)
        (self.output / "result.json").write_text("[]")
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.sdk.responses.create.assert_not_called()

    def test_legacy_judged_record_skips(self):
        self.response()
        self.run_problem()
        saved = self.record()
        saved["judge"] = {"status": "TLE"}
        (self.output / "result.json").write_text(json.dumps(saved))
        self.run_problem()
        self.sdk.responses.create.assert_called_once()

    def test_changed_prompt_aborts_without_second_call(self):
        self.response("No code")
        self.run_problem()
        (self.root / "statement.md").write_text("changed statement")
        with self.assertRaisesRegex(SystemExit, "현재 입력"):
            self.run_problem()
        self.sdk.responses.create.assert_called_once()

    def test_postprocessing_error_records_without_second_call(self):
        response = self.response()
        response.model_dump.side_effect = ValueError("unserializable")
        with self.assertRaisesRegex(SystemExit, "후처리"):
            self.run_problem()
        self.assertFalse(self.record()["record_complete"])
        self.assertEqual(self.record()["processing_error"], {"type": "ValueError"})
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.sdk.responses.create.assert_called_once()

    @patch("subprocess.run", side_effect=AssertionError("candidate must not run"))
    def test_failed_api_response_preserved_and_stops(self, judge):
        self.response("", "failed")
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.assertEqual(self.record()["call"]["status"], "error")
        self.assertTrue((self.output / "response.json").exists())
        judge.assert_not_called()

    def test_malformed_response_metadata_aborts_before_recall(self):
        self.response()
        self.run_problem()
        record = self.record()
        record["model"] = []
        (self.output / "result.json").write_text(json.dumps(record))
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.sdk.responses.create.assert_called_once()
