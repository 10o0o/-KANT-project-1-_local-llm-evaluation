import os
import unittest
from unittest.mock import patch

from llm_eval.cloud import client


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
        self.assertEqual(
            sdk.call_args.kwargs,
            {
                "api_key": "test-only-placeholder",
                "base_url": "https://api.openai.com/v1",
                "timeout": 3600,
                "max_retries": 0,
            },
        )

    @patch.dict(os.environ, {"morph_secret_key": "motif-only-placeholder"}, clear=True)
    @patch("llm_eval.cloud.client.OpenAI")
    def test_each_provider_uses_its_own_key_and_endpoint(self, sdk):
        client.create_client(client.PROVIDERS["motif3"])
        self.assertEqual(
            sdk.call_args.kwargs,
            {
                "api_key": "motif-only-placeholder",
                "base_url": "https://api-cbt.morphfactory.io/v1",
                "timeout": 3600,
                "max_retries": 0,
            },
        )
        sdk.reset_mock()
        # The Luna key is absent, so no Luna client is built from the Morph key.
        with self.assertRaises(SystemExit):
            client.create_client()
        sdk.assert_not_called()

    def test_unknown_model_is_named_without_guessing_a_default(self):
        with self.assertRaisesRegex(ValueError, "지원하지 않는 Cloud 모델"):
            client.get_provider("motif-3")

    def test_request_shape_matches_each_api_family(self):
        luna = client.build_request(client.PROVIDERS["luna"], "prompt")
        motif = client.build_request(client.PROVIDERS["motif3"], "prompt")
        self.assertEqual(luna["input"], [{"role": "user", "content": "prompt"}])
        self.assertNotIn("messages", luna)
        # Only the two fields the provider guide documents are sent.
        self.assertEqual(
            motif,
            {
                "model": "motif/motif-3",
                "messages": [{"role": "user", "content": "prompt"}],
            },
        )
