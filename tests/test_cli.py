import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_eval import cli


class CommandTests(unittest.TestCase):
    def test_help_never_resolves_checkout_or_dispatches(self):
        commands = [[], ['generate'], ['generate', 'local'], ['generate', 'cloud'],
                    ['queue'], ['warmup'], ['judge'], ['judge', 'batch'],
                    ['judge', 'candidate'], ['validate'], ['diagnose'],
                    ['diagnose', 'response'], ['diagnose', 'generation-limit']]
        for command in commands:
            with self.subTest(command=command), patch.object(cli, 'project_root') as root, \
                    patch.object(cli, 'dispatch') as dispatch, \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exit:
                cli.main([*command, '--help'])
            self.assertEqual(exit.exception.code, 0)
            root.assert_not_called()
            dispatch.assert_not_called()

    def test_argument_contracts(self):
        cloud = cli.parse_args(['generate', 'cloud', '--model', 'luna', '--problems', 'all'])
        self.assertEqual((cloud.round, cloud.model), (1, 'luna'))
        self.assertEqual(cli.parse_args(['queue']).startup_timeout_seconds, 900)
        batch = cli.parse_args(['judge', 'batch'])
        self.assertEqual((batch.problems, batch.models, batch.rounds), ('all', 'all', 'all'))
        for args in [[], ['generate', 'local', '--model', 'gemma4', '--problems', 'all'],
                     ['generate', 'cloud', '--model', 'luna', '--problems', 'all', '--round', '3'],
                     ['generate', 'cloud', '--problems', 'all'],
                     ['generate', 'cloud', '--model', 'gpt-luna', '--problems', 'all'],
                     ['warmup', '--model', 'unknown'], ['judge', 'candidate']]:
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as exit:
                cli.parse_args(args)
            self.assertEqual(exit.exception.code, 2)

    def test_wrong_checkout_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cli.Path, 'cwd', return_value=Path(folder)), \
                patch.object(cli, 'dispatch') as dispatch, self.assertRaisesRegex(SystemExit, '저장소 루트'):
            cli.main(['generate', 'cloud', '--model', 'luna', '--problems', 'all'])
        dispatch.assert_not_called()

    def test_root_is_callers_checkout_not_package_location(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pyproject.toml').write_text('[project]\nname="local-llm-evaluation"\n')
            (root / 'src/llm_eval').mkdir(parents=True)
            (root / 'data/coci').mkdir(parents=True)
            (root / 'data/coci/problems.json').write_text('[]')
            with patch.object(cli.Path, 'cwd', return_value=root):
                self.assertEqual(cli.project_root(), root)

    def test_dispatch_preserves_selection_and_round(self):
        cases = [
            (['generate','local','--model','gemma4','--problems','p1','--round','2'],
             'llm_eval.local.generation.run_selected', ('gemma4','p1',2)),
            (['generate','cloud','--model','motif3','--problems','p1','--round','2'],
             'llm_eval.cloud.generation.run_selected', ('motif3','p1',2)),
            (['queue'], 'llm_eval.local.queue.run_queue', (900,)),
            (['warmup','--model','gemma4'], 'llm_eval.local.client.run_warmup', ('gemma4',)),
            (['judge','batch'], 'llm_eval.judging.workflow.run_batch_judging', ('all','all','all')),
            (['judge','candidate','--code','answer.py','--problem','p1'],
             'llm_eval.judging.workflow.run_candidate_check', (Path('answer.py'),'p1')),
            (['diagnose','response'], 'llm_eval.diagnostics.run_response_probe', ()),
            (['diagnose','generation-limit','--model','gemma4'],
             'llm_eval.diagnostics.run_generation_limit_probe', ('gemma4',)),
        ]
        for command, target, expected in cases:
            with self.subTest(command=command), patch(target) as workflow:
                cli.dispatch(Path('/fixture'), cli.parse_args(command))
                workflow.assert_called_once_with(Path('/fixture'), *expected)

class WorkflowBoundaryTests(unittest.TestCase):
    def test_diagnostics_cannot_call_server_when_local_lock_is_refused(self):
        from llm_eval import diagnostics
        for function, arguments, target in [
            (diagnostics.run_response_probe, (), '_response_probe'),
            (diagnostics.run_generation_limit_probe, ('gemma4',), '_generation_limit_probe'),
        ]:
            with self.subTest(function=function.__name__), \
                    patch.object(diagnostics, 'workload', side_effect=RuntimeError('busy')), \
                    patch.object(diagnostics, target) as probe, self.assertRaisesRegex(RuntimeError, 'busy'):
                function(Path('/fixture'), *arguments)
            probe.assert_not_called()

    def test_judging_does_not_collect_or_execute_before_lock(self):
        from llm_eval.judging import workflow
        with patch.object(workflow, 'workload', side_effect=RuntimeError('busy')), \
                patch.object(workflow, '_run_batch') as batch, \
                patch.object(workflow, 'load_problems') as load:
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                workflow.run_batch_judging(Path('/fixture'))
            with self.assertRaisesRegex(RuntimeError, 'busy'):
                workflow.run_candidate_check(Path('/fixture'), Path('answer.py'), 'p')
        batch.assert_not_called()
        load.assert_not_called()
