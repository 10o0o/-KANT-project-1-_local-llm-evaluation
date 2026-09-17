import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.local import queue
from llm_eval.shared import processes


class WorkloadLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_owned_lock_exports_child_fd_and_releases_once(self):
        with (
            patch.object(processes, "ensure_workload_safe") as safe,
            patch.object(processes.fcntl, "flock") as flock,
            processes.workload(self.root, "queue") as lease,
        ):
            self.assertFalse(lease.borrowed)
            self.assertEqual(lease.child_pass_fds(), (lease.fd,))
            self.assertEqual(
                lease.child_env({"EXISTING": "yes"}),
                {"EXISTING": "yes", processes.WORKLOAD_FD_ENV: str(lease.fd)},
            )
            os.fstat(lease.fd)

        self.assertEqual(safe.call_count, 2)
        self.assertEqual(
            [call.args[1] for call in flock.call_args_list],
            [fcntl.LOCK_EX | fcntl.LOCK_NB, fcntl.LOCK_UN],
        )
        with self.assertRaises(OSError):
            os.fstat(lease.fd)

    def test_valid_inherited_fd_is_borrowed_and_never_unlocked_or_closed(self):
        lock_path = processes.workload_lock_path(self.root)
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a+") as inherited, patch.dict(
            os.environ, {processes.WORKLOAD_FD_ENV: str(inherited.fileno())}, clear=False
        ), patch.object(processes, "ensure_workload_safe") as safe, patch.object(
            processes.fcntl, "flock", side_effect=[BlockingIOError(), None]
        ) as flock:
            with processes.workload(
                self.root, "local", allow_inherited=True
            ) as lease:
                self.assertTrue(lease.borrowed)
                self.assertEqual(lease.fd, inherited.fileno())
            os.fstat(inherited.fileno())

        safe.assert_called_once()
        self.assertEqual(len(flock.call_args_list), 2)
        self.assertTrue(all(call.args[1] == fcntl.LOCK_EX | fcntl.LOCK_NB
                            for call in flock.call_args_list))

    def test_same_file_but_another_description_holds_lock_is_rejected(self):
        lock_path = processes.workload_lock_path(self.root)
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a+") as inherited, patch.dict(
            os.environ, {processes.WORKLOAD_FD_ENV: str(inherited.fileno())}
        ), patch.object(processes.fcntl, "flock", side_effect=BlockingIOError):
            with self.assertRaisesRegex(RuntimeError, "다른 실행"):
                with processes.workload(self.root, "local", allow_inherited=True):
                    pass

    def test_unlocked_inherited_fd_fails_closed(self):
        lock_path = processes.workload_lock_path(self.root)
        lock_path.parent.mkdir(parents=True)
        with lock_path.open("a+") as inherited, patch.dict(
            os.environ, {processes.WORKLOAD_FD_ENV: str(inherited.fileno())}, clear=False
        ), patch.object(processes.fcntl, "flock") as flock:
            with self.assertRaisesRegex(RuntimeError, "보유하지"):
                with processes.workload(self.root, "local", allow_inherited=True):
                    pass
        self.assertEqual(
            [call.args[1] for call in flock.call_args_list],
            [fcntl.LOCK_EX | fcntl.LOCK_NB, fcntl.LOCK_UN],
        )

    def test_only_local_and_warmup_may_allow_inheritance(self):
        with self.assertRaises(ValueError):
            with processes.workload(self.root, "cloud", allow_inherited=True):
                pass

    def test_invalid_or_wrong_inherited_fd_fails_closed(self):
        cases = ["not-an-fd", "999999"]
        for value in cases:
            with self.subTest(value=value), patch.dict(
                os.environ, {processes.WORKLOAD_FD_ENV: value}, clear=False
            ), patch.object(processes.fcntl, "flock") as flock:
                with self.assertRaises(RuntimeError):
                    with processes.workload(self.root, "local", allow_inherited=True):
                        pass
                flock.assert_not_called()

        wrong = self.root / "wrong.lock"
        with wrong.open("a+") as stream, patch.dict(
            os.environ, {processes.WORKLOAD_FD_ENV: str(stream.fileno())}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                with processes.workload(self.root, "local", allow_inherited=True):
                    pass

    def test_inherited_fd_is_rejected_when_not_allowed(self):
        with patch.dict(
            os.environ, {processes.WORKLOAD_FD_ENV: "12"}, clear=False
        ), patch.object(processes.fcntl, "flock") as flock:
            with self.assertRaises(RuntimeError):
                with processes.workload(self.root, "cloud"):
                    pass
            flock.assert_not_called()
