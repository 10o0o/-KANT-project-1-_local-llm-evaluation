import os
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.judging import engine
from llm_eval.judging.execution import CollectedProcessOutput, ProcessCleanupError


@unittest.skipUnless(
    os.environ.get("LLM_EVAL_RUN_PROCESS_TESTS") == "1",
    "set LLM_EVAL_RUN_PROCESS_TESTS=1 for real subprocess tests",
)
class EngineProcessIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.input_path = self.root / "case.in.1"
        self.output_path = self.root / "case.out.1"
        self.input_path.write_text("", encoding="utf-8")
        self.output_path.write_text("expected\n", encoding="utf-8")

    def run_script(self, source, *, timeout=2):
        code_path = self.root / "candidate.py"
        code_path.write_text(source, encoding="utf-8")
        return engine.run_test_case(
            code_path, self.input_path, self.output_path, timeout
        )

    def test_real_process_combined_output_limit_is_ole(self):
        six_mib = 6 * 1024 * 1024
        result = self.run_script(
            "import sys\n"
            f"sys.stdout.buffer.write(b'a' * {six_mib})\n"
            f"sys.stderr.buffer.write(b'b' * {six_mib})\n"
        )

        self.assertEqual(result["status"], "OLE")
        self.assertEqual(result["termination_reason"], "output_limit")
        self.assertTrue(result["output_limit_exceeded"])
        self.assertLessEqual(
            len(result["stdout"].encode()) + len(result["stderr"].encode()),
            engine.OUTPUT_LIMIT_BYTES,
        )

    def test_real_stdout_only_and_stderr_only_overflow_are_ole(self):
        overflow = engine.OUTPUT_LIMIT_BYTES + 1
        for stream in ("stdout", "stderr"):
            with self.subTest(stream=stream):
                result = self.run_script(
                    "import sys\n"
                    f"sys.{stream}.buffer.write(b'x' * {overflow})\n"
                )
                self.assertEqual(result["status"], "OLE")
                self.assertEqual(result["termination_reason"], "output_limit")

    def test_parent_exit_cleans_real_descendant_holding_pipes(self):
        marker = "llm-eval-synthetic-descendant"
        result = self.run_script(
            "import subprocess, sys\n"
            "child = subprocess.Popen(\n"
            "    [sys.executable, '-c', 'import time; time.sleep(60)', "
            f"'{marker}'],\n"
            "    stdout=sys.stdout, stderr=sys.stderr,\n"
            ")\n"
            "print(child.pid, flush=True)\n"
        )
        child_pid = int(result["stdout"].strip())

        def child_is_live():
            try:
                state = (Path("/proc") / str(child_pid) / "stat").read_text().split()[2]
            except (FileNotFoundError, ProcessLookupError):
                return False
            return state != "Z"

        def cleanup_child():
            if not child_is_live():
                return
            try:
                cmdline = (Path("/proc") / str(child_pid) / "cmdline").read_bytes()
                if marker.encode() in cmdline:
                    os.kill(child_pid, signal.SIGKILL)
            except (FileNotFoundError, ProcessLookupError):
                pass

        self.addCleanup(cleanup_child)
        deadline = time.monotonic() + 1
        while child_is_live() and time.monotonic() < deadline:
            time.sleep(0.01)

        self.assertFalse(child_is_live())
        self.assertTrue(result["pipes_drained"])

    def test_real_process_deadline_before_later_output_is_tle(self):
        result = self.run_script(
            "import sys, time\n"
            "sys.stdout.write('prefix')\n"
            "sys.stdout.flush()\n"
            "time.sleep(60)\n",
            timeout=0.05,
        )

        self.assertEqual(result["status"], "TLE")
        self.assertEqual(result["termination_reason"], "timeout")
        self.assertTrue(result["timed_out"])
        self.assertFalse(result["output_limit_exceeded"])

    def test_real_process_reads_stdin_file_descriptor(self):
        self.input_path.write_text("hello\n", encoding="utf-8")
        self.output_path.write_text("hello\n", encoding="utf-8")

        result = self.run_script("import sys\nsys.stdout.write(sys.stdin.read())\n")

        self.assertEqual(result["status"], "AC")

    def test_resource_verdict_decodes_truncated_diagnostic_with_replacement(self):
        result = self.run_script(
            "import sys, time\n"
            "sys.stdout.buffer.write(b'\\xff')\n"
            "sys.stdout.buffer.flush()\n"
            "time.sleep(60)\n",
            timeout=0.05,
        )

        self.assertEqual(result["status"], "TLE")
        self.assertEqual(result["stdout"], "\ufffd")

    def test_normal_completion_requires_strict_utf8(self):
        with self.assertRaises(UnicodeDecodeError):
            self.run_script("import sys\nsys.stdout.buffer.write(b'\\xff')\n")


class EngineInfrastructureFailureTests(unittest.TestCase):
    @patch.object(engine, "collect_bounded_output")
    @patch.object(engine, "spawn_isolated")
    def test_elapsed_deadline_starts_before_spawn(self, spawn, collect):
        process = Mock()
        spawn.return_value = process
        collect.return_value = CollectedProcessOutput(
            stdout=b"expected\n",
            stderr=b"",
            returncode=0,
            elapsed_seconds=1.0,
            timed_out=False,
            output_limit_exceeded=False,
            pipes_drained=True,
            termination_reason=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = root / "candidate.py"
            input_path = root / "case.in.1"
            output_path = root / "case.out.1"
            for path in (code, input_path):
                path.write_text("", encoding="utf-8")
            output_path.write_text("expected\n", encoding="utf-8")

            with patch.object(engine, "time", create=True) as clock:
                clock.monotonic.return_value = 123.5
                result = engine.run_test_case(code, input_path, output_path, 2)

        self.assertEqual(result["status"], "AC")
        self.assertEqual(collect.call_args.kwargs["started_at"], 123.5)
    def test_undrained_pipes_raise_infrastructure_error(self):
        collected = CollectedProcessOutput(
            stdout=b"",
            stderr=b"",
            returncode=-9,
            elapsed_seconds=1.0,
            timed_out=True,
            output_limit_exceeded=False,
            pipes_drained=False,
            termination_reason="timeout",
        )
        process = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = root / "candidate.py"
            input_path = root / "case.in.1"
            output_path = root / "case.out.1"
            for path in (code, input_path, output_path):
                path.write_text("", encoding="utf-8")
            with (
                patch.object(engine, "spawn_isolated", return_value=process),
                patch.object(engine, "collect_bounded_output", return_value=collected),
                self.assertRaises(ProcessCleanupError),
            ):
                engine.run_test_case(code, input_path, output_path, 1)


if __name__ == "__main__":
    unittest.main()
