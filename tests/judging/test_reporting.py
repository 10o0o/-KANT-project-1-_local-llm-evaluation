import copy
import unittest

from llm_eval.judging.reporting import build_report, render_markdown


def result(status='AC', elapsed=0.1):
    return {'status': status, 'passed_cases': int(status == 'AC'), 'total_cases': 1,
            'max_case_seconds': elapsed, 'time_limit_seconds': 1,
            'test_results': [{'status': status, 'elapsed_seconds': elapsed}]}


def example():
    policy = {'models': ['qwen36', 'gemma4', 'luna', 'motif3'],
              'local_models': ['qwen36', 'gemma4'], 'planned_attempts_per_model': 20,
              'minimum_valid_originals': 12}
    manifest = {'evaluation_id': 'example', 'policy': policy, 'entries': []}
    states = {}
    for model in policy['local_models']:
        for i in range(20):
            key = f'{model}/{i}'
            manifest['entries'].append({'key': key, 'model': model, 'problem_id': f'p{i // 2}',
                'round': 1 + i % 2, 'source_run_id': key, 'candidate_path': f'{key}.py',
                'official_limit_seconds': 1, 'effective_limit_seconds': 1,
                'needs_limit_run': False, 'limit_role': 'diagnostic'})
            states[key] = {'record': {'call': {'status': 'success'}, 'extracted_code': 'print(1)',
                                     'metrics': {'response_elapsed_seconds': 10}},
                           'baseline': result(), 'review': {'explanation': {'score': 2, 'evidence': '원본 풀이 근거'},
                            'repair': {'decision': None, 'reason': '', 'algorithm_preserved': None, 'code_path': None}},
                           'attempts': [], 'current_repair_sha256': None}
    return manifest, states


def attempt(kind, status='AC', **values):
    return {'attempt_id': 'a1', 'kind': kind, 'status': 'completed',
            'effective_limit_seconds': 2, 'candidate_sha256': 'fixed',
            'result': result(status), 'review': {}, **values}


class ReportingTests(unittest.TestCase):
    def test_cloud_missing_does_not_prevent_ready_local_tie_or_shrink_denominator(self):
        manifest, states = example()
        report = build_report(manifest, states)
        self.assertTrue(report['local_comparison_ready'])
        self.assertEqual(report['local_metric_order'], [['qwen36', 'gemma4']])
        self.assertFalse(report['complete'])
        self.assertEqual(report['models']['luna']['missing'], 20)
        self.assertEqual(report['models']['luna']['planned'], 20)
        self.assertIsNone(report['models']['luna']['explanation']['mean'])
        self.assertIsNone(report['models']['luna']['minimum_quality_pass'])
        self.assertIn('공식 AC', render_markdown(report))

    def test_scoring_override_counts_2x_ac_but_diagnostic_does_not(self):
        manifest, states = example()
        for entry in manifest['entries'][:2]:
            entry['needs_limit_run'] = True
            states[entry['key']]['baseline'] = result('TLE')
            states[entry['key']]['attempts'] = [attempt('limits')]
        manifest['entries'][0].update(limit_role='scoring', effective_limit_seconds=2)
        report = build_report(manifest, states)['models']['qwen36']
        self.assertEqual(report['baseline_ac'], 18)
        self.assertEqual(report['project_valid'], 19)
        self.assertEqual(report['project_valid_rate'], 19 / 20)
        self.assertEqual(report['diagnostic_2x']['ac'], 1)
        self.assertEqual(report['scoring_2x']['completed'], 1)

    def test_pending_override_never_falls_back_to_failure_or_completed_comparison(self):
        manifest, states = example()
        manifest['entries'][0].update(needs_limit_run=True, limit_role='scoring', effective_limit_seconds=2)
        states['qwen36/0']['baseline'] = result('TLE')
        report = build_report(manifest, states)
        self.assertIsNone(report['entries'][0]['project_verdict'])
        self.assertEqual(report['models']['qwen36']['pending_project_verdicts'], 1)
        self.assertIsNone(report['models']['qwen36']['minimum_quality_pass'])
        self.assertIsNone(report['local_metric_order'])

    def test_missing_explanation_is_not_zero_and_bool_is_not_score(self):
        manifest, states = example()
        states['qwen36/0']['review']['explanation'] = {'score': None, 'evidence': ''}
        report = build_report(manifest, states)
        self.assertEqual(report['models']['qwen36']['explanation']['n'], 19)
        self.assertEqual(report['models']['qwen36']['explanation']['mean'], 2)
        self.assertFalse(report['local_comparison_ready'])
        states['qwen36/0']['review']['explanation'] = {'score': True, 'evidence': 'x'}
        with self.assertRaises(ValueError):
            build_report(manifest, states)

    def test_failure_duration_is_separate_and_successful_no_code_is_scored(self):
        manifest, states = example()
        s = states['qwen36/0']
        s['record'].update(call={'status': 'error'}, extracted_code=None,
                           metrics={'response_elapsed_seconds': 999})
        s['baseline'] = {'status': 'CALL_ERROR'}
        s['review']['explanation'] = {'score': None, 'evidence': ''}
        manifest['entries'][0]['candidate_path'] = None
        states['qwen36/1']['record']['extracted_code'] = None
        states['qwen36/1']['baseline'] = result('NO_CODE')
        manifest['entries'][1]['candidate_path'] = None
        report = build_report(manifest, states)['models']['qwen36']
        self.assertEqual(report['project_valid'], 18)
        self.assertEqual(report['call_error'], 1)
        self.assertEqual(report['no_code'], 1)
        self.assertEqual(report['explanation']['n'], 19)
        self.assertEqual(report['success_response_seconds']['mean'], 10)
        self.assertEqual(report['failure_elapsed_seconds']['mean'], 999)

    def test_duplicate_repairs_count_once_and_new_unjudged_revision_blocks_readiness(self):
        manifest, states = example()
        state = states['qwen36/0']
        state['baseline'] = result('WA')
        state['review']['repair'] = {'decision': 'candidate', 'reason': '경계값',
                                      'algorithm_preserved': True, 'code_path': 'fix.py'}
        state['current_repair_sha256'] = 'fixed'
        a = attempt('repairs', review=copy.deepcopy(state['review']))
        state['attempts'] = [a, {**copy.deepcopy(a), 'attempt_id': 'a2'}]
        report = build_report(manifest, states)
        self.assertEqual(report['models']['qwen36']['project_valid'], 19)
        self.assertEqual(report['models']['qwen36']['repairs']['unique_passes'], 1)
        self.assertEqual(report['models']['qwen36']['repairs']['attempts'], 2)
        self.assertTrue(report['local_comparison_ready'])
        state['review']['explanation'] = {'score': 1, 'evidence': '설명 검토만 수정'}
        self.assertTrue(build_report(manifest, states)['local_comparison_ready'])
        state['current_repair_sha256'] = 'new-code'
        self.assertFalse(build_report(manifest, states)['local_comparison_ready'])

    def test_unrepairable_review_closes_target_without_awarding_pass(self):
        manifest, states = example()
        states['qwen36/0']['baseline'] = result('WA')
        states['qwen36/0']['review']['repair'].update(decision='not_repairable', reason='알고리즘 교체 필요')
        report = build_report(manifest, states)['models']['qwen36']
        self.assertEqual(report['repairs']['reviewed'], 1)
        self.assertEqual(report['repairs']['unique_passes'], 0)
        self.assertTrue(report['comparison_ready'])

    def test_equal_limit_is_not_valid_and_missing_timing_blocks_rank(self):
        manifest, states = example()
        states['qwen36/0']['baseline'] = result(elapsed=1)
        report = build_report(manifest, states)
        self.assertEqual(report['models']['qwen36']['project_ac'], 20)
        self.assertEqual(report['models']['qwen36']['project_valid'], 19)
        self.assertTrue(report['models']['qwen36']['errors'])
        self.assertFalse(report['local_comparison_ready'])
        states['qwen36/0']['baseline'] = result()
        states['qwen36/0']['record']['metrics']['response_elapsed_seconds'] = None
        self.assertFalse(build_report(manifest, states)['local_comparison_ready'])


class ReportPersistenceTests(unittest.TestCase):
    def test_reports_snapshot_reviews_and_attempts_without_executing_candidates(self):
        import contextlib
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from llm_eval.judging import evaluation
        from llm_eval.judging.reporting import report_evaluation
        from llm_eval.shared.storage import write_json
        from tests.judging.evaluation_helpers import build_evaluation_fixture, completed_result

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build_evaluation_fixture(root)
            folder = evaluation.prepare_evaluation(root, 'baseline')
            review_path = folder / 'reviews/a/qwen36/round_1/review.json'
            review = json.loads(review_path.read_text())
            review['explanation'] = {'score': 2, 'evidence': 'fixture 원본 근거'}
            write_json(review_path, review)
            with patch.object(evaluation, 'judge_problem') as judge:
                first = report_evaluation(root, folder.name)
                judge.assert_not_called()
            before = (first / 'report.json').read_bytes()
            with patch.object(evaluation, 'workload', side_effect=lambda *a, **k: contextlib.nullcontext()), \
                    patch.object(evaluation, 'judge_problem', return_value=completed_result('AC')):
                evaluation.run_evaluation(root, folder.name, 'limits')
            second = report_evaluation(root, folder.name)
            self.assertNotEqual(first, second)
            self.assertEqual((first / 'report.json').read_bytes(), before)
            report = json.loads((second / 'report.json').read_text())
            self.assertEqual(report['models']['qwen36']['project_valid'], 1)
            self.assertEqual(report['models']['qwen36']['missing'], 1)
            self.assertEqual(report['models']['qwen36']['explanation']['n'], 1)
            self.assertFalse(report['complete'])
            self.assertTrue((second / 'review-snapshot.json').is_file())
            candidate = root / 'results/benchmark/a/qwen36/round_1/candidate.py'
            candidate.write_text('tamper')
            count = len(list((folder / 'reports').iterdir()))
            with self.assertRaises(ValueError):
                report_evaluation(root, folder.name)
            self.assertEqual(len(list((folder / 'reports').iterdir())), count)
