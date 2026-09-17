import contextlib
import io
import json
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from llm_eval.local import queue, server
from llm_eval.local.runner import request_conditions
from llm_eval.shared.storage import write_json


class QueueTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        (self.root / 'data/coci').mkdir(parents=True)
        (self.root / 'statement.md').write_text('example')
        self.problems = [{'id': f'id_{i}', 'name': f'p{i}', 'title': 'example', 'difficulty': 1,
                          'statement_path': 'statement.md', 'problem_dir': 'testdata',
                          'time_limit_seconds': 1, 'memory_limit_mib': 512, 'judge_type': 'token'} for i in range(10)]
        write_json(self.root / 'data/coci/problems.json', self.problems)
        config = self.root / 'configs/llama.cpp'
        config.mkdir(parents=True)
        for model in queue.MODELS:
            (config / f'{model}.sh').write_text(f'exec llama-server --alias {model}\n')
        self.enterContext(patch('llm_eval.shared.processes.ensure_workload_safe'))
        self.idle = self.enterContext(patch.object(queue, 'check_idle'))
        self.stop = self.enterContext(patch.object(queue, 'stop_owned'))
        self.free = self.enterContext(patch.object(queue, 'wait_port_free'))
        self.port = self.enterContext(patch.object(queue, 'port_busy', return_value=False))
        self.enterContext(patch.object(queue.subprocess, 'run'))  # shell syntax boundary only
        self.ready = self.enterContext(patch.object(queue, 'wait_ready', return_value=['llama-server']))
        self.spawn = self.enterContext(patch.object(queue.LocalQueue, 'spawn'))
        self.spawn.return_value = Mock(pid=123)
        self.commands = []
        self.command = self.enterContext(patch.object(queue.LocalQueue, 'command', side_effect=self.generate))

    def record(self, problem, model, number, error=False):
        folder = self.root / f"results/benchmark/{problem['name']}/{model}/round_{number}"
        folder.mkdir(parents=True, exist_ok=True)
        req, config = request_conditions(self.root, problem)
        write_json(folder / 'result.json', {
            'record_complete': True, 'call': {'status': 'error' if error else 'success'},
            'request': req, 'generation_config': config, 'model': {'id': model},
            'problem': {'id': problem['id']}, 'experiment': {'type': 'benchmark', 'round': number},
            'generation': None if error else {'finish_reason': 'length'}, 'extracted_code': None, 'judge': None,
        })
        if not error:
            write_json(folder / 'response.json', {})
        return folder

    def generate(self, args, log):
        self.commands.append(args)
        if args[0] == 'scripts/run_local_benchmark.py':
            model, number = args[2], int(args[-1])
            for problem in self.problems:
                folder = self.root / f"results/benchmark/{problem['name']}/{model}/round_{number}"
                if not folder.exists():
                    self.record(problem, model, number)
            if model == 'qwen36' and number == 2:
                (self.root / 'configs/llama.cpp/gemma4.sh').write_text('exec llama-server --alias gemma4 --gpu-layers auto\n')

    def status(self):
        return json.loads(next((self.root / 'logs/local_queue').glob('*/status.json')).read_text())

    def test_sequence_resume_latest_shell_and_no_cloud_or_judge(self):
        folder = self.record(self.problems[0], 'qwen36', 1)
        original = (folder / 'result.json').read_bytes()
        session = queue.run_queue(self.root)
        self.assertEqual([(a[0], a[2], a[-1]) for a in self.commands], [
            ('scripts/run_warmup.py', 'qwen36', 'qwen36'),
            ('scripts/run_local_benchmark.py', 'qwen36', '1'),
            ('scripts/run_local_benchmark.py', 'qwen36', '2'),
            ('scripts/run_warmup.py', 'gemma4', 'gemma4'),
            ('scripts/run_local_benchmark.py', 'gemma4', '1'),
            ('scripts/run_local_benchmark.py', 'gemma4', '2'),
        ])
        self.assertEqual((folder / 'result.json').read_bytes(), original)
        self.assertIn('--gpu-layers auto', (session / 'gemma4.server.sh').read_text())
        self.assertEqual(self.spawn.call_args.args[0], ['bash', str(session / 'gemma4.server.sh')])
        self.assertEqual(self.status()['status'], 'completed')
        self.assertTrue(self.status()['finished_at'])
        self.assertEqual(self.free.call_count, 2)
        self.assertFalse(any('judge' in a[0] or 'cloud' in a[0] for a in self.commands))

    def test_all_complete_starts_nothing(self):
        for model in queue.MODELS:
            for number in (1, 2):
                for problem in self.problems:
                    self.record(problem, model, number)
        queue.run_queue(self.root)
        self.spawn.assert_not_called()
        self.command.assert_not_called()

    def test_failed_or_incomplete_record_blocks_before_server(self):
        folder = self.record(self.problems[0], 'qwen36', 1, error=True)
        with self.assertRaisesRegex(RuntimeError, '호출 실패'):
            queue.run_queue(self.root)
        (folder / 'result.json').unlink()
        with self.assertRaisesRegex(SystemExit, 'incomplete'):
            queue.run_queue(self.root)
        self.spawn.assert_not_called()
        self.assertFalse(list((self.root / 'logs/local_queue').glob('*/status.json')))

    def test_mismatch_and_missing_raw_block(self):
        folder = self.record(self.problems[0], 'qwen36', 1)
        (self.root / 'statement.md').write_text('changed')
        with self.assertRaisesRegex(SystemExit, '입력·설정'):
            queue.run_queue(self.root)
        (self.root / 'statement.md').write_text('example')
        (folder / 'response.json').unlink()
        with self.assertRaisesRegex(SystemExit, 'incomplete'):
            queue.run_queue(self.root)
        self.spawn.assert_not_called()

    def test_child_success_without_results_stops(self):
        self.command.side_effect = None
        with self.assertRaisesRegex(RuntimeError, '미완료'):
            queue.run_queue(self.root)
        self.assertEqual(self.command.call_count, 2)  # warmup + first round only
        self.assertEqual(self.status()['status'], 'error')
        self.stop.assert_any_call(self.spawn.return_value)

    def test_warmup_failure_or_interrupt_cleans_owned_server(self):
        self.command.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            queue.run_queue(self.root)
        self.assertEqual(self.command.call_count, 1)
        self.assertEqual(self.status()['status'], 'interrupted')
        self.stop.assert_any_call(self.spawn.return_value)

    def test_startup_failure_stops_without_commands(self):
        self.ready.side_effect = RuntimeError('not ready')
        with self.assertRaisesRegex(RuntimeError, 'not ready'):
            queue.run_queue(self.root)
        self.command.assert_not_called()
        self.assertEqual(self.status()['status'], 'error')
        self.stop.assert_any_call(self.spawn.return_value)

    def test_duplicate_queue_and_external_workload_block(self):
        with queue.queue_lock(self.root / 'logs/local_queue'):
            with self.assertRaisesRegex(RuntimeError, '실행 중'):
                queue.run_queue(self.root)
        self.idle.side_effect = RuntimeError('active local')
        with self.assertRaisesRegex(RuntimeError, 'active local'):
            queue.run_queue(self.root)
        self.spawn.assert_not_called()
