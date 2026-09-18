import contextlib
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval.cloud import generation


class SelectionTests(unittest.TestCase):
    def run_selected(self, *, model="luna", round_number=None):
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
            patch.object(generation, "create_client", return_value=client_context) as factory,
            patch.object(generation, "run_problem") as run_problem,
        ):
            if round_number is None:
                generation.run_selected(root, model, "p1")
            else:
                generation.run_selected(root, model, "p1", round_number)
        return run_problem, factory

    def test_round_defaults_to_demo(self):
        run_problem, _ = self.run_selected()
        self.assertIsNone(run_problem.call_args.kwargs["round_number"])

    def test_explicit_round_one_is_forwarded(self):
        run_problem, _ = self.run_selected(round_number=1)
        self.assertEqual(run_problem.call_args.kwargs["round_number"], 1)

    def test_round_two_is_forwarded(self):
        run_problem, _ = self.run_selected(round_number=2)
        self.assertEqual(run_problem.call_args.kwargs["round_number"], 2)

    def test_selected_provider_reaches_client_and_runner(self):
        for model in ("luna", "motif3"):
            with self.subTest(model=model):
                run_problem, factory = self.run_selected(model=model)
                self.assertEqual(run_problem.call_args.kwargs["provider"].key, model)
                self.assertEqual(factory.call_args.args[0].key, model)

    def test_invalid_round_is_rejected_before_work(self):
        with patch.object(generation, "workload") as workload:
            with self.assertRaisesRegex(ValueError, "1 또는 2"):
                generation.run_selected(Path("/fixture"), "luna", "p1", 3)
        workload.assert_not_called()

    def test_unknown_model_is_rejected_before_work(self):
        with patch.object(generation, "workload") as workload:
            with self.assertRaisesRegex(ValueError, "지원하지 않는 Cloud 모델"):
                generation.run_selected(Path("/fixture"), "gpt-luna", "p1", 1)
        workload.assert_not_called()
