import contextlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

class ScriptSafetyTests(unittest.TestCase):
    def test_diagnostic_import_does_not_create_client(self):
        with patch('openai.OpenAI') as sdk, contextlib.redirect_stdout(io.StringIO()):
            for relative in ('scripts/diagnose.py', 'scripts/diagnostics/response_probe.py',
                             'scripts/calibration/run_stress_test.py',
                             'scripts/diagnostics/generation_limit_probe.py'):
                runpy.run_path(str(ROOT / relative), run_name='import_probe')
        sdk.assert_not_called()

    def test_invalid_problem_is_never_printed_ok(self):
        namespace = runpy.run_path(str(ROOT / 'scripts/validate_dataset.py'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            (root / 'data/coci').mkdir(parents=True)
            (root / 'statement.md').write_text('example')
            (root / 'p.in.1').write_text('1')
            problem = {field: 'placeholder' for field in namespace['REQUIRED_FIELDS']}
            problem.update(id='broken', name='p', difficulty=1, judge_type='token',
                           statement_path='statement.md', problem_dir='.')
            (root / 'data/coci/problems.json').write_text(json.dumps([problem]))
            function = namespace['main']
            function.__globals__['__file__'] = str(root / 'scripts/validate_dataset.py')
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                function()
            self.assertNotIn('[OK] broken', output.getvalue())
            self.assertIn('missing outputs', output.getvalue())
            (root / 'p.out.1').write_text('1')
            (root / 'data/coci/problems.json').write_text(json.dumps([problem, problem]))
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                function()
            self.assertNotIn('[OK] broken', output.getvalue())
            self.assertIn('duplicate problem id', output.getvalue())

    def test_compatibility_scripts_forward_to_canonical_paths(self):
        pairs = {
            'scripts/run_benchmark.py': 'scripts/run_local_benchmark.py',
            'scripts/run_judge.py': 'scripts/run_batch_judge.py',
            'scripts/diagnose.py': 'scripts/diagnostics/response_probe.py',
            'scripts/calibration/run_stress_test.py': 'scripts/diagnostics/generation_limit_probe.py',
        }
        for old, new in pairs.items():
            with self.subTest(old=old):
                namespace = runpy.run_path(str(ROOT / old), run_name='import_only')
                with patch('runpy.run_path') as forward:
                    namespace['main']()
                self.assertEqual(Path(forward.call_args.args[0]).resolve(), (ROOT / new).resolve())
                self.assertEqual(forward.call_args.kwargs, {'run_name': '__main__'})
