import contextlib
import io
import json
from pathlib import Path
import importlib
from llm_eval import cli
from llm_eval.shared import problems
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

class ScriptSafetyTests(unittest.TestCase):
    def test_diagnostic_import_does_not_create_client(self):
        with patch('openai.OpenAI') as sdk, contextlib.redirect_stdout(io.StringIO()):
            importlib.reload(importlib.import_module('llm_eval.diagnostics'))
        sdk.assert_not_called()

    def test_invalid_problem_is_never_printed_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            (root / 'data/coci').mkdir(parents=True)
            (root / 'statement.md').write_text('example')
            (root / 'p.in.1').write_text('1')
            problem = {field: 'placeholder' for field in problems.REQUIRED_FIELDS}
            problem.update(id='broken', name='p', difficulty=1, judge_type='token',
                           statement_path='statement.md', problem_dir='.')
            (root / 'data/coci/problems.json').write_text(json.dumps([problem]))
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                cli.dispatch(root, cli.parse_args(['validate']))
            self.assertNotIn('[OK] broken', output.getvalue())
            self.assertIn('missing outputs', output.getvalue())
            (root / 'p.out.1').write_text('1')
            (root / 'data/coci/problems.json').write_text(json.dumps([problem, problem]))
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                cli.dispatch(root, cli.parse_args(['validate']))
            self.assertNotIn('[OK] broken', output.getvalue())
            self.assertIn('duplicate problem id', output.getvalue())
