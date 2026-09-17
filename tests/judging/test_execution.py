import selectors
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from llm_eval.judging import execution as judge_process


class FakePipe:
    def __init__(self, fd):
        self._fd = fd
        self.closed = False

    def fileno(self):
        return self._fd

    def close(self):
        self.closed = True


class FakeSelector:
    def __init__(self, selections):
        self.selections = list(selections)
        self.registered = {}
        self.timeouts = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def register(self, pipe, events, data):
        self.registered[pipe] = SimpleNamespace(fileobj=pipe, data=data)

    def unregister(self, pipe):
        return self.registered.pop(pipe)

    def get_map(self):
        return self.registered

    def select(self, timeout=None):
        self.timeouts.append(timeout)
        selected = self.selections.pop(0) if self.selections else []
        return [(self.registered[pipe], selectors.EVENT_READ) for pipe in selected]


def fake_process(*, returncode=None):
    process = Mock(pid=4321, returncode=returncode)
    process.stdout = FakePipe(10)
    process.stderr = FakePipe(11)
    process.poll.return_value = returncode
    return process


class SpawnTests(unittest.TestCase):
    @patch.object(judge_process.subprocess, "Popen")
    def test_spawn_uses_new_session_and_separate_binary_pipes(self, popen):
        expected = Mock()
        popen.return_value = expected

        actual = judge_process.spawn_isolated(["python", "candidate.py"], cwd="sandbox")

        self.assertIs(actual, expected)
        popen.assert_called_once_with(
            ["python", "candidate.py"],
            cwd="sandbox",
            env=None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            close_fds=True,
            restore_signals=True,
            start_new_session=True,
        )


class CleanupTests(unittest.TestCase):
    def test_group_liveness_ignores_zombies_but_detects_live_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc_root = Path(temporary)
            process_dir = proc_root / "123"
            process_dir.mkdir()
            stat = process_dir / "stat"
            stat.write_text("123 (fixture child) S 1 4321 4321 0")
            self.assertTrue(judge_process._group_has_live_members(4321, proc_root))
            stat.write_text("123 (fixture child) Z 1 4321 4321 0")
            self.assertFalse(judge_process._group_has_live_members(4321, proc_root))

    @patch.object(judge_process.os, "killpg")
    def test_cleanup_rejects_non_finite_timeouts_before_signaling(self, killpg):
        process = fake_process()
        for name in ("grace_seconds", "kill_wait_seconds"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    judge_process.terminate_process_group(process, **{name: value})
        killpg.assert_not_called()

    @patch.object(judge_process.os, "killpg")
    def test_term_timeout_escalates_to_kill_for_the_owned_group(self, killpg):
        process = fake_process()
        process.wait.side_effect = [
            subprocess.TimeoutExpired("candidate", 0.25),
            -signal.SIGKILL,
        ]
        process.poll.side_effect = [None, None]

        judge_process.terminate_process_group(
            process, grace_seconds=0.25, kill_wait_seconds=1.0
        )

        self.assertEqual(
            killpg.call_args_list,
            [call(4321, signal.SIGTERM), call(4321, 0), call(4321, signal.SIGKILL)],
        )
        self.assertEqual(
            process.wait.call_args_list, [call(timeout=0.25), call(timeout=1.0)]
        )

    @patch.object(judge_process.os, "killpg")
    def test_exited_leader_still_cleans_lingering_descendants(self, killpg):
        process = fake_process(returncode=0)

        judge_process.terminate_process_group(process)

        self.assertEqual(
            killpg.call_args_list,
            [call(4321, signal.SIGTERM), call(4321, 0), call(4321, signal.SIGKILL)],
        )
        process.wait.assert_not_called()


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.process = fake_process(returncode=-signal.SIGKILL)
        self.process.poll.return_value = None
        self.selector = FakeSelector(
            [
                [self.process.stdout],
                [self.process.stderr],
                [self.process.stdout, self.process.stderr],
            ]
        )

    def collect(self, **kwargs):
        reads = {10: [b"abc", b""], 11: [b"1234", b""]}

        def read(fd, size):
            return reads[fd].pop(0)

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking") as set_blocking,
            patch.object(judge_process.os, "read", side_effect=read) as os_read,
            patch.object(judge_process, "terminate_process_group") as terminate,
        ):
            result = judge_process.collect_bounded_output(
                self.process,
                timeout_seconds=5,
                output_limit_bytes=kwargs.get("output_limit_bytes", 5),
            )
        return result, set_blocking, os_read, terminate

    def test_collection_rejects_unbounded_or_non_integer_limits_before_io(self):
        process = Mock(stdout=None, stderr=None)
        finite_fields = (
            "timeout_seconds",
            "cleanup_grace_seconds",
            "cleanup_wait_seconds",
            "drain_timeout_seconds",
        )
        defaults = {"timeout_seconds": 1, "output_limit_bytes": 1}
        with patch.object(judge_process.os, "set_blocking") as set_blocking:
            for name in finite_fields:
                for value in (float("nan"), float("inf"), float("-inf")):
                    kwargs = {**defaults, name: value}
                    with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                        judge_process.collect_bounded_output(process, **kwargs)
            for value in (True, 1.5, "1"):
                with self.subTest(output_limit_bytes=value), self.assertRaises(TypeError):
                    judge_process.collect_bounded_output(
                        process, timeout_seconds=1, output_limit_bytes=value
                    )
        set_blocking.assert_not_called()

    def test_aggregate_cap_keeps_prefix_kills_group_and_drains_both_pipes(self):
        result, set_blocking, os_read, terminate = self.collect()

        self.assertEqual((result.stdout, result.stderr), (b"abc", b"12"))
        self.assertEqual(result.termination_reason, "output_limit")
        self.assertTrue(result.output_limit_exceeded)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.pipes_drained)
        self.assertEqual(result.returncode, -signal.SIGKILL)
        self.assertEqual(set_blocking.call_args_list, [call(10, False), call(11, False)])
        self.assertEqual(os_read.call_count, 4)  # EOF is consumed after the cap.
        terminate.assert_called_once_with(
            self.process, grace_seconds=0.25, kill_wait_seconds=1.0
        )

    def test_timeout_is_bounded_then_cleanup_still_drains_eof(self):
        self.process = fake_process(returncode=-signal.SIGKILL)
        self.process.poll.return_value = None
        self.selector = FakeSelector(
            [[], [self.process.stdout, self.process.stderr]]
        )
        reads = {10: [b""], 11: [b""]}
        clock = iter([0.0, 0.0, 0.0, 2.1, 2.2, 2.3, 2.4])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group") as terminate,
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=2, output_limit_bytes=100
            )

        self.assertTrue(result.timed_out)
        self.assertEqual(result.termination_reason, "timeout")
        self.assertFalse(result.output_limit_exceeded)
        self.assertTrue(result.pipes_drained)
        self.assertAlmostEqual(self.selector.timeouts[0], 2.0)
        terminate.assert_called_once()

    def test_elapsed_stops_at_timeout_before_cleanup_and_drain(self):
        self.process = fake_process(returncode=-signal.SIGKILL)
        self.process.poll.return_value = None
        self.selector = FakeSelector([[], [self.process.stdout, self.process.stderr]])
        reads = {10: [b""], 11: [b""]}
        # Timeout is observed at 2.1. Cleanup and pipe draining advance the
        # clock, but candidate elapsed time must retain the first trigger.
        clock = iter([0.0, 0.0, 0.0, 2.1, 2.2, 4.0, 4.1, 4.2])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group"),
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=2, output_limit_bytes=100
            )

        self.assertEqual(result.termination_reason, "timeout")
        self.assertAlmostEqual(result.elapsed_seconds, 2.1)

    def test_timeout_first_keeps_bounded_diagnostic_without_becoming_ole(self):
        self.process = fake_process(returncode=-signal.SIGKILL)
        self.process.poll.return_value = None
        self.selector = FakeSelector(
            [[], [self.process.stdout], [self.process.stdout, self.process.stderr]]
        )
        reads = {10: [b"abcdef", b""], 11: [b""]}
        clock = iter([0.0, 0.0, 0.0, 2.1, 2.2, 2.3, 2.4, 2.5])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group"),
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=2, output_limit_bytes=3
            )

        self.assertEqual(result.stdout, b"abc")
        self.assertEqual(result.termination_reason, "timeout")
        self.assertTrue(result.timed_out)
        self.assertFalse(result.output_limit_exceeded)

    def test_selector_wake_at_deadline_beats_ready_output_overflow(self):
        self.process = fake_process(returncode=-signal.SIGKILL)
        self.process.poll.return_value = None
        self.selector = FakeSelector(
            [[self.process.stdout], [self.process.stdout, self.process.stderr]]
        )
        reads = {10: [b"abcdef", b""], 11: [b""]}
        clock = iter([0.0, 0.0, 2.1, 2.2, 2.3, 2.4, 2.5])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group"),
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=2, output_limit_bytes=3
            )

        self.assertEqual(result.termination_reason, "timeout")
        self.assertTrue(result.timed_out)
        self.assertFalse(result.output_limit_exceeded)

    def test_normal_exit_elapsed_is_not_overwritten_by_drain_overflow(self):
        self.process = fake_process(returncode=0)
        self.selector = FakeSelector(
            [[self.process.stdout], [self.process.stdout, self.process.stderr]]
        )
        reads = {10: [b"abcdef", b""], 11: [b""]}
        clock = iter([0.0, 0.1, 2.0, 2.1, 3.0, 3.1, 3.2])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group"),
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=10, output_limit_bytes=3
            )

        self.assertEqual(result.termination_reason, "output_limit")
        self.assertAlmostEqual(result.elapsed_seconds, 0.1)

    def test_parent_exit_also_cleans_descendants_before_pipe_drain(self):
        self.process = fake_process(returncode=0)
        self.selector = FakeSelector([[self.process.stdout, self.process.stderr]])
        reads = {10: [b""], 11: [b""]}

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)),
            patch.object(judge_process, "terminate_process_group") as terminate,
        ):
            result = judge_process.collect_bounded_output(
                self.process, timeout_seconds=2, output_limit_bytes=100
            )

        self.assertFalse(result.timed_out)
        self.assertTrue(result.pipes_drained)
        terminate.assert_called_once()

    def test_lingering_open_pipes_have_a_separate_bounded_drain_window(self):
        self.process = fake_process(returncode=0)
        self.selector = FakeSelector([[]])
        # Cleanup itself consumes 0.4 seconds. The select timeout must be based
        # on a fresh 0.5 sample, not the stale pre-cleanup 0.0 sample.
        clock = iter([0.0, 0.0, 0.4, 0.5, 1.5, 1.6, 1.7])

        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(judge_process, "terminate_process_group") as terminate,
        ):
            result = judge_process.collect_bounded_output(
                self.process,
                timeout_seconds=10,
                output_limit_bytes=100,
                drain_timeout_seconds=1,
            )

        self.assertFalse(result.timed_out)
        self.assertFalse(result.pipes_drained)
        self.assertAlmostEqual(self.selector.timeouts[0], 0.9)
        terminate.assert_called_once()
        self.assertTrue(self.process.stdout.closed)
        self.assertTrue(self.process.stderr.closed)

    def test_read_error_cleans_group_and_closes_pipes(self):
        self.selector = FakeSelector([[self.process.stdout]])
        with (
            patch.object(judge_process.selectors, "DefaultSelector", return_value=self.selector),
            patch.object(judge_process.os, "set_blocking"),
            patch.object(judge_process.os, "read", side_effect=OSError("read failed")),
            patch.object(judge_process, "terminate_process_group") as terminate,
        ):
            with self.assertRaisesRegex(OSError, "read failed"):
                judge_process.collect_bounded_output(
                    self.process, timeout_seconds=2, output_limit_bytes=100
                )

        terminate.assert_called_once()
        self.assertTrue(self.process.stdout.closed)
        self.assertTrue(self.process.stderr.closed)


if __name__ == "__main__":
    unittest.main()
