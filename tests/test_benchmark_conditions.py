import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.benchmark import runner
from llm_eval.benchmark.prompts import build_round1_prompt
from llm_eval.benchmark.utils import prepare_problem_context
from llm_eval.cloud import runner as cloud_runner
from llm_eval.llama_cpp import REASONING_BUDGET_MESSAGE, chat


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
        expected = build_round1_prompt(
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
            with self.subTest(field=field), patch.object(runner, field, value):
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
            path = prepare_problem_context(self.root, self.problem, model, number)[-1]
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


if __name__ == '__main__':
    unittest.main()
