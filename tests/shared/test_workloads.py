from llm_eval.judging import workflow as batch
import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.local import queue
from llm_eval.shared import workloads as processes


class ProcessScannerTests(unittest.TestCase):
    def test_evaluation_execution_is_judge_but_preparation_and_reports_are_not(self):
        for command in ('llm-eval', '/tmp/checkout/.venv/bin/llm-eval'):
            self.assertEqual(processes._runner_kind([command, 'evaluate', 'run', '--evaluation', 'id', '--kind', 'limits']), 'judge')
            for action in ('prepare', 'report'):
                self.assertIsNone(processes._runner_kind([command, 'evaluate', action]))

    def test_unified_cli_forms_classify_all_workloads(self):
        commands = [
            (["generate", "local"], "local"), (["generate", "cloud"], "cloud"),
            (["queue"], "queue"), (["warmup"], "warmup"),
            (["evaluate", "run"], "judge"), (["evaluate", "prepare"], None),
            (["evaluate", "report"], None), (["evaluate", "run", "--help"], None),
            (["judge", "batch"], "judge"), (["judge", "candidate"], "judge"),
            (["diagnose", "response"], "local"),
            (["diagnose", "generation-limit"], "local"), (["validate"], None),
            (["generate", "cloud", "--help"], None),
        ]
        prefixes = [["/venv/bin/llm-eval"], ["python3", "/venv/bin/llm-eval"],
                    ["uv", "run", "--env-file", "example.env", "llm-eval"],
                    ["python3", "-m", "llm_eval"], ["uv", "run", "python", "-m", "llm_eval"]]
        for prefix in prefixes:
            for command, expected in commands:
                with self.subTest(argv=prefix + command):
                    self.assertEqual(processes._runner_kind(prefix + command), expected)


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

    def test_conflict_matrix_allows_cloud_with_local_workloads_and_server(self):
        allowed_pairs = (
            ("local", ["python3", "scripts/run_cloud_benchmark.py"]),
            ("local", ["/bin/llama-server", "--alias", "qwen36"]),
            ("warmup", ["python3", "scripts/run_cloud_benchmark.py"]),
            ("warmup", ["/bin/llama-server", "--alias", "qwen36"]),
            ("queue", ["python3", "scripts/run_cloud_benchmark.py"]),
            ("cloud", ["python3", "scripts/run_benchmark.py"]),
            ("cloud", ["python3", "scripts/run_warmup.py"]),
            ("cloud", ["python3", "scripts/run_local_queue.py"]),
            ("cloud", ["/bin/llama-server", "--alias", "qwen36"]),
        )
        for index, (kind, argv) in enumerate(allowed_pairs, 201):
            with self.subTest(kind=kind, active=argv[1]):
                self.process(index, argv)
                try:
                    processes.ensure_workload_safe(
                        kind, self.proc, excluded_pids=set()
                    )
                finally:
                    (self.proc / str(index) / "cmdline").unlink()

        self.process(299, ["python3", "scripts/run_batch_judge.py"])
        for kind in processes.WORKLOAD_KINDS:
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                processes.ensure_workload_safe(kind, self.proc, excluded_pids=set())

    def test_duplicate_and_same_lane_workloads_conflict(self):
        cases = {
            "local": ["python3", "scripts/run_local_queue.py"],
            "warmup": ["python3", "scripts/run_benchmark.py"],
            "queue": ["python3", "scripts/run_warmup.py"],
            "cloud": ["python3", "scripts/run_cloud_benchmark.py"],
        }
        for index, (kind, argv) in enumerate(cases.items(), 301):
            with self.subTest(kind=kind):
                child = self.proc / str(index)
                child.mkdir()
                (child / "cmdline").write_bytes(
                    b"\0".join(item.encode() for item in argv) + b"\0"
                )
                with self.assertRaises(RuntimeError):
                    processes.ensure_workload_safe(
                        kind, self.proc, excluded_pids=set()
                    )
                (child / "cmdline").unlink()

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
