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

class CostTests(unittest.TestCase):
    def cost(self, data):
        return estimated_cost(data, client.LUNA.model, "default")

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
        for model, tier in [("unknown", "default"), (client.LUNA.model, "priority"), (None, None)]:
            self.assertIsNone(estimated_cost(usage(), model, tier)["estimated_usd"])
