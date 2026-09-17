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

from llm_eval.shared.prompts import build_problem_prompt
from llm_eval.cloud import client, runner
from llm_eval.cloud.metrics import estimated_cost


from .helpers import usage

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
