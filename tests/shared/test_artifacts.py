"""File consistency rules, independent from request identity and retry policy."""
import json
from pathlib import Path
import tempfile
import unittest

from llm_eval.shared.artifacts import validate_artifacts


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
