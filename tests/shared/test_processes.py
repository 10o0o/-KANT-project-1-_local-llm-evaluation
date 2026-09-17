from llm_eval.judging import batch
import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.local import queue
from llm_eval.shared import processes


class ProcessScannerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.proc = Path(temporary.name)

    def process(self, pid, argv):
        folder = self.proc / str(pid)
        folder.mkdir()
        (folder / "cmdline").write_bytes(b"\0".join(x.encode() for x in argv) + b"\0")

    def test_cross_checkout_runner_is_detected_but_shell_text_is_ignored(self):
        self.process(101, ["python3", "/other/checkout/scripts/run_benchmark.py"])
        self.process(102, ["bash", "-c", "cat scripts/run_benchmark.py"])
        found = processes.active_workloads(self.proc, excluded_pids=set())
        self.assertEqual([(item["pid"], item["kind"]) for item in found], [(101, "local")])

    def test_server_allowance_depends_on_workload_kind(self):
        self.process(201, ["/bin/llama-server", "--alias", "qwen36"])
        processes.ensure_workload_safe("local", self.proc, excluded_pids=set())
        processes.ensure_workload_safe("warmup", self.proc, excluded_pids=set())
        for kind in ("queue", "cloud", "judge"):
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                processes.ensure_workload_safe(kind, self.proc, excluded_pids=set())

    @patch.object(processes.os, "killpg", side_effect=AssertionError("must not signal"))
    def test_conflict_never_signals_discovered_process(self, kill):
        self.process(301, ["python3", "/other/scripts/run_cloud_benchmark.py"])
        with self.assertRaises(RuntimeError):
            processes.ensure_workload_safe("judge", self.proc, excluded_pids=set())
        kill.assert_not_called()


    def test_process_matching_ignores_shell_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = [b"/bin/llama-server\0--model\0x", b"python3\0scripts/run_benchmark.py",
                        b"python3\0scripts/run_cloud_benchmark.py", b"bash\0-c\0cat scripts/run_benchmark.py"]
            for i, command in enumerate(commands, 900001):
                folder = root / str(i)
                folder.mkdir()
                (folder / "cmdline").write_bytes(command)
            self.assertEqual([x["pid"] for x in batch.active_workloads(root)], [900001, 900002, 900003])
