import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.local import generation as runner
from llm_eval.shared.problems import build_problem_prompt
from llm_eval.shared.artifacts import generation_dir
from llm_eval.cloud import generation as cloud_runner
from llm_eval.local import client as local_client
from llm_eval.local.client import REASONING_BUDGET_MESSAGE, chat


class BenchmarkConditionsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.statement = self.root / 'statement.md'
        self.statement.write_text('Problem body', encoding='utf-8')
        self.problem = {
            'id': 'p', 'name': 'p', 'title': 'PRIVATE TITLE', 'difficulty': 9,
            'time_limit_seconds': 3.0, 'memory_limit_mib': 512,
            'judge_type': 'token', 'problem_dir': 'tests',
            'statement_path': 'statement.md',
        }
        response = Mock()
        response.model_dump.return_value = {
            'choices': [{'finish_reason': 'stop', 'message': {'content': 'No code'}}],
        }
        self.call = self.enterContext(patch.object(runner, 'chat', return_value=response))
        self.enterContext(patch.object(runner, 'safe_memory', return_value={}))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.path = self.root / 'results/benchmark/p/qwen36/round_1/result.json'

    def run_local(self):
        runner.run_problem(self.root, self.problem, 'qwen36', 1, Mock())

    def test_same_local_cloud_prompt_and_layout(self):
        self.run_local()
        expected = build_problem_prompt(
            'Problem body', time_limit_seconds=3, memory_limit_mib=512
        )
        self.assertIn('실행 제한:\n- 시간 제한: 3초\n- 메모리 제한: 512 MiB\n\n문제:\n\nProblem body', expected)
        self.assertNotIn('PRIVATE TITLE', expected)
        self.assertEqual(self.call.call_args.args[2], expected)
        sdk = Mock()
        sdk.responses.create.return_value.output_text = ''
        sdk.responses.create.return_value.model_dump.return_value = {'status': 'completed'}
        cloud_runner.run_problem(self.root, self.problem, sdk)
        self.assertEqual(sdk.responses.create.call_args.kwargs['input'][0]['content'], expected)
        self.assertTrue((self.root / 'results/benchmark/p/luna/round_1/result.json').exists())
        original = self.path.read_bytes()
        self.run_local()
        self.call.assert_called_once()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse((self.root / 'results/benchmark/round_1').exists())

    def test_code_is_saved_without_immediate_judging(self):
        (self.root / "tests").mkdir()
        (self.root / "tests/p.in.1").write_text("1")
        (self.root / "tests/p.out.1").write_text("1")
        self.call.return_value.model_dump.return_value = {
            "choices": [{"finish_reason": "stop", "message": {
                "content": "```python\nprint(1)\n```"}}],
        }
        with patch("subprocess.run", side_effect=AssertionError("candidate must not run")):
            self.run_local()
        saved = json.loads(self.path.read_text())
        self.assertTrue(saved["record_complete"])
        self.assertIsNone(saved["judge"])
        self.assertEqual(self.path.with_name("candidate.py").read_text(), "print(1)")
        self.run_local()
        self.call.assert_called_once()

    def test_legacy_judged_record_skips_but_false_marker_blocks(self):
        self.run_local()
        saved = json.loads(self.path.read_text())
        saved.pop("record_complete")
        saved["judge"] = {"status": "TLE"}
        self.path.write_text(json.dumps(saved))
        self.run_local()
        saved["record_complete"] = False
        self.path.write_text(json.dumps(saved))
        with self.assertRaisesRegex(SystemExit, "incomplete"):
            self.run_local()
        self.call.assert_called_once()

    def test_local_changes_abort_without_call(self):
        self.run_local()
        original = self.path.read_bytes()
        self.statement.write_text('Changed', encoding='utf-8')
        with self.assertRaisesRegex(SystemExit, '입력·설정'):
            self.run_local()
        self.statement.write_text('Problem body', encoding='utf-8')
        for field, value in [('time_limit_seconds', 1.5), ('memory_limit_mib', 256)]:
            with self.subTest(field=field):
                old = self.problem[field]
                self.problem[field] = value
                with self.assertRaisesRegex(SystemExit, '입력·설정'):
                    self.run_local()
                self.problem[field] = old
        for field, value in [('MAX_TOKENS', 100), ('REASONING_BUDGET_TOKENS', 50),
                             ('TEMPERATURE', 1), ('REASONING_BUDGET_MESSAGE', 'changed')]:
            with self.subTest(field=field), patch.object(local_client, field, value):
                with self.assertRaisesRegex(SystemExit, '입력·설정'):
                    self.run_local()
        for field, key, value in [('model', 'id', 'gemma4'),
                                  ('generation_config', 'cache_prompt', True)]:
            saved = json.loads(original)
            saved[field][key] = value
            self.path.write_text(json.dumps(saved), encoding='utf-8')
            with self.assertRaisesRegex(SystemExit, '입력·설정'):
                self.run_local()
        self.path.write_bytes(original)
        self.call.assert_called_once()

    def test_failure_records_message_and_skips(self):
        self.call.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            self.run_local()
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['generation_config']['reasoning_budget_message'], REASONING_BUDGET_MESSAGE)
        self.run_local()
        self.call.assert_called_once()

    def test_incomplete_does_not_call(self):
        self.path.parent.mkdir(parents=True)
        with self.assertRaisesRegex(SystemExit, 'incomplete'):
            self.run_local()
        self.call.assert_not_called()

    def test_distinct_models_and_rounds(self):
        for model, number in [('qwen36', 1), ('qwen36', 2), ('gemma4', 1)]:
            path = generation_dir(self.root, self.problem["name"], model, number)
            self.assertEqual(path, self.root / f'results/benchmark/p/{model}/round_{number}')

    def test_request_and_saved_config_match(self):
        self.run_local()
        sdk = Mock()
        chat(sdk, 'qwen36', 'prompt')
        sent = sdk.chat.completions.create.call_args.kwargs
        saved = json.loads(self.path.read_text())['generation_config']
        self.assertEqual(sent['max_tokens'], 61440)
        self.assertEqual(sent['extra_body']['reasoning_budget_tokens'], 53248)
        self.assertEqual(saved, {'temperature': sent['temperature'],
                                'max_tokens': sent['max_tokens'], **sent['extra_body']})
