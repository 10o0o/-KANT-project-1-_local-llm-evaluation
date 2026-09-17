import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.local import queue
from llm_eval.shared import processes


class QueueInheritanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.lease = Mock()
        self.lease.child_env.return_value = {processes.WORKLOAD_FD_ENV: "7"}
        self.lease.child_pass_fds.return_value = (7,)
        self.queue = queue.LocalQueue(self.root, self.logs, 10, self.lease)
        self.addCleanup(
            lambda: [handle.close() for handle in self.queue.handles if not handle.closed]
        )

    @patch.object(queue.subprocess, "Popen")
    def test_spawn_passes_lock_only_when_explicitly_requested(self, popen):
        popen.return_value = Mock(pid=123)
        self.queue.spawn(["python", "child.py"], "child.log", inherit_lock=True)
        child_kwargs = popen.call_args.kwargs
        self.assertEqual(child_kwargs["pass_fds"], (7,))
        self.assertEqual(child_kwargs["env"][processes.WORKLOAD_FD_ENV], "7")

        self.queue.spawn(["bash", "server.sh"], "server.log")
        server_kwargs = popen.call_args.kwargs
        self.assertNotIn("pass_fds", server_kwargs)
        self.assertNotIn("env", server_kwargs)

    def test_command_marks_local_and_warmup_children_for_inheritance(self):
        child = Mock(returncode=0)
        child.poll.return_value = 0
        with patch.object(self.queue, "spawn", return_value=child) as spawn:
            self.queue.command(["scripts/run_warmup.py", "--model", "qwen36"], "warmup.log")
        self.assertIs(spawn.call_args.kwargs["inherit_lock"], True)
