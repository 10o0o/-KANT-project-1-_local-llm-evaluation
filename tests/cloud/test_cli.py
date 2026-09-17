import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.cloud import cli


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        root = Path("/fixture")
        problems = [{"id": "p1"}]
        client = Mock()
        client_context = Mock()
        client_context.__enter__ = Mock(return_value=client)
        client_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(sys, "argv", ["run_cloud_benchmark.py", "--problems", "p1", *arguments]),
            patch.object(cli, "load_problems", return_value=problems),
            patch.object(cli, "select_problems", return_value=problems),
            patch.object(cli, "workload", return_value=contextlib.nullcontext()),
            patch.object(cli, "create_client", return_value=client_context),
            patch.object(cli, "run_problem") as run_problem,
        ):
            cli.main(root)
        return run_problem

    def test_round_defaults_to_one(self):
        run_problem = self.run_cli()
        run_problem.assert_called_once_with(
            Path("/fixture"), {"id": "p1"}, run_problem.call_args.args[2], ["p1"],
            round_number=1,
        )

    def test_round_two_is_forwarded(self):
        run_problem = self.run_cli("--round", "2")
        self.assertEqual(run_problem.call_args.kwargs, {"round_number": 2})

    def test_invalid_round_is_rejected_before_work(self):
        with (
            patch.object(sys, "argv", ["run_cloud_benchmark.py", "--problems", "p1", "--round", "3"]),
            patch.object(cli, "workload") as workload,
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            cli.main(Path("/fixture"))
        self.assertEqual(raised.exception.code, 2)
        workload.assert_not_called()
