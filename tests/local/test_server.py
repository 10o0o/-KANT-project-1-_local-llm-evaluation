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


class LifecycleTests(unittest.TestCase):
    def test_spawn_interrupt_keeps_ownership_without_blocking_child_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = queue.LocalQueue(Path(tmp), Path(tmp), 10)
            child = Mock(pid=123)
            def create(*args, **kwargs):
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                return child
            with patch.object(server.subprocess, 'Popen', side_effect=create):
                with self.assertRaises(KeyboardInterrupt):
                    obj.spawn(['fake'], 'server.log')
            self.assertEqual(obj.owned, [child])
            for handle in obj.handles:
                handle.close()

    def test_idle_excludes_wrapper_but_blocks_external_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '123').mkdir()
            (root / '123/cmdline').write_bytes(b'uv\0run\0python\0scripts/run_local_queue.py\0')
            with patch.object(queue, 'ancestors', return_value={123}), patch.object(queue, 'port_busy', return_value=False):
                queue.check_idle(root)
                (root / '456').mkdir()
                (root / '456/cmdline').write_bytes(b'python\0scripts/run_cloud_benchmark.py\0')
                queue.check_idle(root)
                (root / '789').mkdir()
                (root / '789/cmdline').write_bytes(b'python\0scripts/run_benchmark.py\0')
                with self.assertRaisesRegex(RuntimeError, '789'):
                    queue.check_idle(root)

    def test_server_death_during_generation_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = queue.LocalQueue(Path(tmp), Path(tmp), 10)
            obj.server = Mock()
            obj.server.poll.return_value = 1
            child = Mock()
            child.poll.return_value = None
            with patch.object(obj, 'spawn', return_value=child):
                with self.assertRaisesRegex(RuntimeError, '서버가 종료'):
                    obj.command(['fake'], 'run.log')
            self.assertIs(obj.client, child)

    @patch.object(server, 'actual_argv', return_value=['llama-server'])
    @patch.object(server, 'owns_server_port', return_value=True)
    @patch.object(server, 'http_json')
    @patch.object(server.time, 'sleep')
    def test_loading_then_ready(self, sleep, http, owns, argv):
        process = Mock(pid=123)
        process.poll.return_value = None
        http.side_effect = [URLError('loading'), {'status': 'ok'}, {'data': [{'id': 'gemma4'}]}]
        self.assertEqual(server.wait_ready(process, 'gemma4', 10), ['llama-server'])
        owns.assert_called_once_with(123)

    @patch.object(server, 'http_json')
    @patch.object(server, 'owns_server_port', return_value=False)
    def test_wrong_alias_or_owner_rejected(self, owns, http):
        process = Mock(pid=123)
        process.poll.return_value = None
        for model in ('qwen36', 'gemma4'):
            http.side_effect = [{'status': 'ok'}, {'data': [{'id': model}]}]
            with self.assertRaises(RuntimeError):
                server.wait_ready(process, 'gemma4', 10)

    def test_early_exit_and_timeout(self):
        process = Mock(returncode=1)
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, '조기 종료'):
            server.wait_ready(process, 'qwen36', 10)
        with patch.object(server.time, 'monotonic', side_effect=[0, 20]):
            with self.assertRaisesRegex(RuntimeError, '시간 초과'):
                server.wait_ready(process, 'qwen36', 10)

    @patch.object(server.os, 'killpg')
    def test_only_owned_process_group_terminated_and_timeout_is_error(self, kill):
        process = Mock(pid=123)
        process.poll.return_value = None
        server.stop_owned(process)
        kill.assert_called_once_with(123, signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=60)
        kill.reset_mock()
        process.wait.side_effect = [subprocess.TimeoutExpired('server', 60), 0]
        with self.assertRaisesRegex(RuntimeError, '강제 종료'):
            server.stop_owned(process)
        self.assertEqual([call.args for call in kill.call_args_list], [(123, signal.SIGTERM), (123, signal.SIGKILL)])
        kill.reset_mock()
        process.poll.return_value = 0
        server.stop_owned(process)
        kill.assert_not_called()

    @patch.object(server, 'port_busy', return_value=True)
    @patch.object(server.time, 'monotonic', side_effect=[0, 20])
    def test_port_not_released_aborts(self, clock, busy):
        with self.assertRaisesRegex(RuntimeError, '8080'):
            server.wait_port_free()

    def test_command_nonzero_stops_and_uses_current_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = queue.LocalQueue(Path(tmp), Path(tmp), 10)
            child = Mock(returncode=7)
            child.poll.return_value = 7
            with patch.object(obj, 'spawn', return_value=child) as spawn:
                with self.assertRaisesRegex(RuntimeError, '실행 실패'):
                    obj.command(['scripts/run_warmup.py', '--model', 'qwen36'], 'warm.log')
                self.assertEqual(spawn.call_args.args[0][0], queue.sys.executable)
