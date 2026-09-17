import contextlib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.cloud import generation


class SelectionTests(unittest.TestCase):
    def run_selected(self, *, round_number=1):
        root = Path("/fixture")
        problems = [{"id": "p1"}]
        client = Mock()
        client_context = Mock()
        client_context.__enter__ = Mock(return_value=client)
        client_context.__exit__ = Mock(return_value=False)
        with (
            patch.object(generation, "load_problems", return_value=problems),
            patch.object(generation, "select_problems", return_value=problems),
            patch.object(generation, "workload", return_value=contextlib.nullcontext()),
            patch.object(generation, "create_client", return_value=client_context),
            patch.object(generation, "run_problem") as run_problem,
        ):
            generation.run_selected(root, "p1", round_number)
        return run_problem

    def test_round_defaults_to_one(self):
        run_problem = self.run_selected()
        self.assertEqual(run_problem.call_args.kwargs, {"round_number": 1})

    def test_round_two_is_forwarded(self):
        run_problem = self.run_selected(round_number=2)
        self.assertEqual(run_problem.call_args.kwargs, {"round_number": 2})

    def test_invalid_round_is_rejected_before_work(self):
        with patch.object(generation, "workload") as workload:
            with self.assertRaisesRegex(ValueError, "1 또는 2"):
                generation.run_selected(Path("/fixture"), "p1", 3)
        workload.assert_not_called()
