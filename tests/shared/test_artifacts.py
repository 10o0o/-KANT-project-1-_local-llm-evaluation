"""File consistency rules, independent from request identity and retry policy."""
import json
from pathlib import Path
import tempfile
import unittest

from llm_eval.shared.artifacts import reset_demo_dir, validate_artifacts


class ArtifactTests(unittest.TestCase):
    def test_received_cloud_response_metadata_cannot_be_replaced(self):
        record = {
            'record_complete': True, 'call': {'status': 'success'},
            'experiment': {'type': 'cloud'},
            'model': {'response_model': 'model'},
            'generation': {'response_id': 'resp_original', 'status': 'completed',
                           'usage': {}, 'service_tier': 'default'},
            'extracted_code': None,
        }
        raw = {'id': 'resp_original', 'status': 'completed', 'model': 'model',
               'usage': {}, 'service_tier': 'default'}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'response.json').write_text(json.dumps(raw))
            validate_artifacts(folder, record)
            for damaged in ({}, {**raw, 'id': 'resp_other'}):
                (folder / 'response.json').write_text(json.dumps(damaged))
                with self.subTest(damaged=damaged), self.assertRaises(ValueError):
                    validate_artifacts(folder, record)

    def test_demo_record_without_planned_attempts_validates(self):
        record = {
            "record_complete": True,
            "call": {"status": "success"},
            "experiment": {"type": "demo", "round": None},
            "model": {
                "runtime": "openai_responses",
                "response_model": "gpt-5.6-luna",
            },
            "generation": {
                "response_id": "resp_demo",
                "status": "completed",
                "usage": {},
                "service_tier": "default",
            },
            "extracted_code": None,
        }
        raw = {
            "id": "resp_demo",
            "status": "completed",
            "model": "gpt-5.6-luna",
            "usage": {},
            "service_tier": "default",
        }
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "response.json").write_text(json.dumps(raw))
            validate_artifacts(folder, record)
        self.assertNotIn("planned_attempts", record["experiment"])

    def test_demo_reset_rejects_symlink_target_without_touching_outside(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("preserve")
            target = root / "results/demo/p/qwen36"
            target.parent.mkdir(parents=True)
            target.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "심볼릭 링크"):
                reset_demo_dir(root, "p", "qwen36")

            self.assertTrue(target.is_symlink())
            self.assertEqual(sentinel.read_text(), "preserve")
