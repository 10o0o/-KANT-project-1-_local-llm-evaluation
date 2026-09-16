import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from openai import APITimeoutError, AuthenticationError

from llm_eval.benchmark.prompts import build_round1_prompt
from llm_eval.cloud import client, runner
from llm_eval.cloud.metrics import estimated_cost


def usage(inputs=1000, read=200, write=100, output=500):
    return {
        "input_tokens": inputs,
        "input_tokens_details": {"cached_tokens": read, "cache_write_tokens": write},
        "output_tokens": output,
        "output_tokens_details": {"reasoning_tokens": 400},
        "total_tokens": inputs + output,
    }


class CostTests(unittest.TestCase):
    def cost(self, data):
        return estimated_cost(data, client.MODEL, "default")

    def test_read_write_and_reasoning_not_double_counted(self):
        # 700*.20 + 200*.02 + 100*.25 + 500*1.20 = 769 microdollars.
        result = self.cost(usage())
        self.assertEqual(result["estimated_usd"], 0.000769)
        self.assertEqual(result["billable_tokens"]["input"], 700)
        self.assertIsNone(result["reason"])

    def test_zero_is_not_missing(self):
        self.assertEqual(self.cost(usage(0, 0, 0, 0))["estimated_usd"], 0)
        self.assertIsNone(self.cost({})["estimated_usd"])

    def test_invalid_or_unsupported_cost_has_reason(self):
        cases = [usage(read=1001), usage(write=-1), usage(inputs=True), usage(inputs=272001)]
        incomplete = usage()
        incomplete["input_tokens_details"].pop("cache_write_tokens")
        cases.append(incomplete)
        for data in cases:
            with self.subTest(data=data):
                result = self.cost(data)
                self.assertIsNone(result["estimated_usd"])
                self.assertTrue(result["reason"])
        for model, tier in [("unknown", "default"), (client.MODEL, "priority"), (None, None)]:
            self.assertIsNone(estimated_cost(usage(), model, tier)["estimated_usd"])


class ClientTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("llm_eval.cloud.client.OpenAI")
    def test_missing_key_does_not_create_client(self, sdk):
        with self.assertRaises(SystemExit):
            client.create_client()
        sdk.assert_not_called()

    @patch.dict(os.environ, {"openai_secret_key": "test-only-placeholder"}, clear=True)
    @patch("llm_eval.cloud.client.OpenAI")
    def test_client_configuration(self, sdk):
        client.create_client()
        self.assertEqual(sdk.call_args.kwargs, {
            "api_key": "test-only-placeholder", "base_url": "https://api.openai.com/v1",
            "timeout": 3600, "max_retries": 0,
        })


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
            "id": "resp_test", "model": client.MODEL, "status": status,
            "service_tier": "default", "usage": usage(),
            "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": content}]}],
        }
        self.sdk.responses.create.return_value = response
        return response

    def run_problem(self):
        return runner.run_problem(self.root, self.problem, self.sdk)

    def record(self):
        return json.loads((self.output / "result.json").read_text())

    @patch("llm_eval.cloud.runner.judge_problem")
    @patch("llm_eval.cloud.runner.perf_counter", side_effect=[10, 12])
    def test_success_same_prompt_raw_before_judge_and_skip(self, clock, judge):
        response = self.response()

        def fake_judge(**kwargs):
            self.assertEqual(json.loads((self.output / "response.json").read_text()), response.model_dump.return_value)
            self.assertEqual(kwargs["code_path"].read_text(), "print(1)")
            return {"status": "AC", "passed_cases": 1, "total_cases": 1}

        judge.side_effect = fake_judge
        self.run_problem()
        request = self.sdk.responses.create.call_args.kwargs
        self.assertEqual(request, {
            "model": "gpt-5.6-luna", "reasoning": {"effort": "max"},
            "max_output_tokens": 128000, "tools": [], "tool_choice": "none",
            "store": False, "service_tier": "default",
            "input": [{"role": "user", "content": build_round1_prompt("same statement", time_limit_seconds=1, memory_limit_mib=512)}],
        })
        record = self.record()
        self.assertEqual(record["judge"]["status"], "AC")
        self.assertEqual(record["metrics"]["response_elapsed_seconds"], 2)
        self.assertIsNone(record["metrics"]["generation_tokens_per_second"])
        self.assertEqual(record["model"]["response_model"], client.MODEL)
        self.assertEqual(record["generation"]["response_id"], "resp_test")
        self.run_problem()
        self.sdk.responses.create.assert_called_once()
        judge.assert_called_once()
        self.assertFalse((self.root / "results/cloud").exists())

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

    @patch("llm_eval.cloud.runner.judge_problem")
    def test_refusal_no_code_and_missing_usage(self, judge):
        response = self.response("", "completed")
        response.model_dump.return_value["usage"] = None
        response.model_dump.return_value["output"] = [{"type": "message", "content": [{"type": "refusal", "refusal": "Cannot answer"}]}]
        self.run_problem()
        record = self.record()
        self.assertEqual(record["judge"]["status"], "NO_CODE")
        self.assertIsNone(record["metrics"]["cost"]["estimated_usd"])
        self.assertFalse((self.output / "candidate.py").exists())
        judge.assert_not_called()

    @patch("llm_eval.cloud.runner.judge_problem", return_value={"status": "RE"})
    def test_incomplete_with_code_is_judged(self, judge):
        self.response(status="incomplete")
        self.run_problem()
        record = self.record()
        self.assertEqual(record["generation"]["status"], "incomplete")
        self.assertEqual(record["judge"]["status"], "RE")
        self.assertEqual(record["generation"]["incomplete_details"]["reason"], "max_output_tokens")

    @patch("llm_eval.cloud.runner.judge_problem")
    def test_incomplete_without_code(self, judge):
        self.response("unfinished answer", "incomplete")
        self.run_problem()
        self.assertEqual(self.record()["judge"]["status"], "NO_CODE")
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

    @patch("llm_eval.cloud.runner.judge_problem", side_effect=OSError("fixture unavailable"))
    def test_judge_failure_keeps_response_and_prevents_paid_retry(self, judge):
        self.response()
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.assertFalse(self.record()["record_complete"])
        self.assertTrue((self.output / "response.json").exists())
        with self.assertRaises(SystemExit):
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

    @patch("llm_eval.cloud.runner.judge_problem")
    def test_failed_api_response_preserved_and_stops(self, judge):
        self.response("", "failed")
        with self.assertRaises(SystemExit):
            self.run_problem()
        self.assertEqual(self.record()["call"]["status"], "error")
        self.assertTrue((self.output / "response.json").exists())
        judge.assert_not_called()


if __name__ == "__main__":
    unittest.main()
