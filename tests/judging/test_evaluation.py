import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_eval.judging import evaluation
from llm_eval.shared.storage import write_json
from tests.judging.evaluation_helpers import (
    build_evaluation_fixture,
    completed_result,
    read_json,
)


class ProjectVerdictTests(unittest.TestCase):
    def test_scoring_tle_requires_completed_limit_attempt(self):
        entry = {"limit_role": "scoring", "needs_limit_run": True}
        baseline = {"status": "TLE"}

        pending = evaluation.project_verdict(entry, {"baseline": baseline, "attempts": []})
        completed = evaluation.project_verdict(
            entry,
            {
                "baseline": baseline,
                "attempts": [
                    {"kind": "limits", "status": "error", "result": {"status": "AC"}},
                    {"kind": "limits", "status": "completed", "result": {"status": "WA"}},
                ],
            },
        )

        self.assertEqual(pending, (None, "pending_limits"))
        self.assertEqual(completed, ({"status": "WA"}, "limit_2x"))


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def prepare(self, **kwargs):
        build_evaluation_fixture(self.root, **kwargs)
        return evaluation.prepare_evaluation(self.root, "baseline")

    def attempts(self, folder, kind=None):
        attempts = [read_json(path) for path in sorted(folder.glob("attempts/**/attempt.json"))]
        return [item for item in attempts if kind is None or item["kind"] == kind]

    def test_prepare_is_sealed_provisional_and_reads_call_error(self):
        folder = self.prepare(call_error=True)
        loaded_folder, manifest = evaluation.load_evaluation(self.root, folder.name)
        self.assertEqual(loaded_folder, folder)
        self.assertEqual(len(manifest["missing"]), 7)
        self.assertIn("a/qwen36/round_2", manifest["missing"])
        self.assertEqual(manifest["entries"][0]["baseline_judge"], None)
        state = evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])
        self.assertEqual(state["baseline"]["status"], "CALL_ERROR")
        self.assertIsNone(state["review"]["repair"]["decision"])

        manifest_path = folder / "manifest.json"
        original = manifest_path.read_bytes()
        manifest_path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(ValueError, "봉인 이후 변경"):
            evaluation.load_evaluation(self.root, folder.name)

    def test_source_mutation_and_path_escape_are_rejected(self):
        folder = self.prepare()
        candidate = self.root / "results/benchmark/a/qwen36/round_1/candidate.py"
        candidate.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source가 변경"):
            evaluation.load_evaluation(self.root, folder.name)
        with self.assertRaisesRegex(ValueError, "baseline ID"):
            evaluation.prepare_evaluation(self.root, "../baseline")

    def test_limits_are_append_only_retryable_and_idempotent(self):
        folder = self.prepare()
        judge = patch.object(evaluation, "judge_problem", return_value=completed_result())
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with judge as mocked, lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")
            evaluation.run_evaluation(self.root, folder.name, "limits")
        self.assertEqual(mocked.call_count, 1)
        attempts = self.attempts(folder, "limits")
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["status"], "completed")
        self.assertEqual(attempts[0]["effective_limit_seconds"], 2)

    def test_judge_error_is_not_completed_and_next_run_retries(self):
        folder = self.prepare()
        infrastructure = {"status": "JUDGE_ERROR", "test_results": []}
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", return_value=infrastructure), lane:
            with self.assertRaisesRegex(RuntimeError, "인프라 오류"):
                evaluation.run_evaluation(self.root, folder.name, "limits")
        with patch.object(evaluation, "judge_problem", return_value=completed_result()), lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")
        self.assertEqual([a["status"] for a in self.attempts(folder, "limits")], ["error", "completed"])

    def test_terminal_attempt_seal_detects_result_tampering(self):
        folder = self.prepare()
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", return_value=completed_result()), lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")
        attempt_path = next(folder.glob("attempts/**/attempt.json"))
        attempt = read_json(attempt_path)
        attempt["result"]["status"] = "AC"
        write_json(attempt_path, attempt)
        with self.assertRaisesRegex(ValueError, "봉인 이후 변경"):
            evaluation.load_evaluation(self.root, folder.name)

    def test_diagnostic_limit_does_not_relax_project_validity_limit(self):
        build_evaluation_fixture(self.root)
        policy_path = self.root / "configs/evaluation.json"
        policy = read_json(policy_path)
        policy["effective_limit_overrides"] = {}
        write_json(policy_path, policy)
        folder = evaluation.prepare_evaluation(self.root, "baseline")
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        entry = manifest["entries"][0]
        self.assertEqual(entry["effective_limit_seconds"], 1)
        self.assertEqual(entry["diagnostic_limit_seconds"], 2)
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", return_value=completed_result()) as mocked, lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")
        self.assertEqual(mocked.call_args.kwargs["time_limit_seconds"], 2)

    def test_later_tle_is_eligible_but_ac_never_reruns(self):
        build_evaluation_fixture(self.root, status="WA", test_statuses=["WA", "TLE"])
        folder = evaluation.prepare_evaluation(self.root, "baseline")
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        self.assertTrue(manifest["entries"][0]["needs_limit_run"])

        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        ac_root = Path(other.name)
        build_evaluation_fixture(ac_root, status="AC")
        ac_folder = evaluation.prepare_evaluation(ac_root, "baseline")
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem") as mocked, lane:
            evaluation.run_evaluation(ac_root, ac_folder.name, "limits")
        mocked.assert_not_called()

    def test_source_change_during_judge_records_error_attempt(self):
        folder = self.prepare()
        source = self.root / "results/benchmark/a/qwen36/round_1/candidate.py"

        def mutate_source(**_kwargs):
            source.write_text("changed during judge\n", encoding="utf-8")
            return completed_result()

        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", side_effect=mutate_source), lane:
            with self.assertRaisesRegex(ValueError, "source가 변경"):
                evaluation.run_evaluation(self.root, folder.name, "limits")
        self.assertEqual(self.attempts(folder, "limits")[0]["status"], "error")

    def test_workload_refusal_executes_nothing(self):
        folder = self.prepare()
        with patch.object(evaluation, "workload", side_effect=RuntimeError("busy")), patch.object(
            evaluation, "judge_problem"
        ) as mocked, self.assertRaisesRegex(RuntimeError, "busy"):
            evaluation.run_evaluation(self.root, folder.name, "limits")
        mocked.assert_not_called()
        self.assertEqual(self.attempts(folder), [])

    def test_interrupt_is_sealed_and_next_run_creates_new_attempt(self):
        folder = self.prepare()
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", side_effect=KeyboardInterrupt()), lane:
            with self.assertRaises(KeyboardInterrupt):
                evaluation.run_evaluation(self.root, folder.name, "limits")
        with patch.object(evaluation, "judge_problem", return_value=completed_result()), lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")
        self.assertEqual(
            [attempt["status"] for attempt in self.attempts(folder, "limits")],
            ["interrupted", "completed"],
        )

    def test_policy_source_can_change_after_snapshot(self):
        folder = self.prepare()
        policy_path = self.root / "configs/evaluation.json"
        policy = read_json(policy_path)
        policy["minimum_valid_originals"] = 2
        write_json(policy_path, policy)
        loaded, _manifest = evaluation.load_evaluation(self.root, folder.name)
        self.assertEqual(loaded, folder)

    def test_review_scalar_types_and_escape_are_rejected(self):
        folder = self.prepare(status="WA")
        review_path = folder / "reviews/a/qwen36/round_1/review.json"
        for field, value in (("score", 1.0), ("score", True)):
            review = read_json(review_path)
            review["explanation"][field] = value
            review["explanation"]["evidence"] = "evidence"
            write_json(review_path, review)
            _, manifest = evaluation.load_evaluation(self.root, folder.name)
            with self.assertRaisesRegex(ValueError, "explanation 값"):
                evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])
        review = read_json(review_path)
        review["explanation"] = {"score": None, "evidence": ""}
        review["repair"].update(
            decision="candidate", reason="fixture", algorithm_preserved=1, code_path="../x.py"
        )
        write_json(review_path, review)
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        with self.assertRaisesRegex(ValueError, "repair 값"):
            evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])
        review["repair"]["algorithm_preserved"] = True
        write_json(review_path, review)
        with self.assertRaisesRegex(ValueError, "저장소 범위"):
            evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])

    def test_baseline_cross_identity_mismatches_are_rejected(self):
        def case_root():
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            root = Path(temporary.name)
            build_evaluation_fixture(root, status="WA")
            return root

        root = case_root()
        manifest_path = root / "results/judging/baseline/manifest.json"
        manifest = read_json(manifest_path)
        manifest["entries"][0]["candidate_path"] = None
        manifest["entries"][0]["candidate_sha256"] = None
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "candidate 존재 여부"):
            evaluation.prepare_evaluation(root, "baseline")

        root = case_root()
        manifest_path = root / "results/judging/baseline/manifest.json"
        manifest = read_json(manifest_path)
        manifest["entries"][0]["status"] = "CALL_ERROR"
        manifest["entries"][0]["judge_path"] = None
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "CALL_ERROR 상태"):
            evaluation.prepare_evaluation(root, "baseline")

        root = case_root()
        judge_path = root / "results/judging/baseline/a/qwen36/round_1/judge.json"
        judge = read_json(judge_path)
        judge["source_sha256"] = "0" * 64
        write_json(judge_path, judge)
        with self.assertRaisesRegex(ValueError, "source/candidate 신원"):
            evaluation.prepare_evaluation(root, "baseline")

        root = case_root()
        manifest_path = root / "results/judging/baseline/manifest.json"
        manifest = read_json(manifest_path)
        manifest["session_id"] = "different"
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "완료된 baseline"):
            evaluation.prepare_evaluation(root, "baseline")

    def test_current_four_override_policy_accepts_ten_problem_metadata(self):
        source_judging = Path(evaluation.__file__).parent
        target_judging = self.root / "src/llm_eval/judging"
        target_judging.mkdir(parents=True)
        for name in ("engine.py", "execution.py", "workflow.py", "evaluation.py"):
            (target_judging / name).write_bytes((source_judging / name).read_bytes())
        policy_source = Path(__file__).parents[2] / "configs/evaluation.json"
        (self.root / "configs").mkdir()
        (self.root / "configs/evaluation.json").write_bytes(policy_source.read_bytes())
        policy = read_json(policy_source)
        override_ids = list(policy["effective_limit_overrides"])
        problems = []
        for number in range(10):
            problem_id = override_ids[number] if number < len(override_ids) else f"other_{number}"
            name = f"p{number}"
            data = self.root / "data" / name
            data.mkdir(parents=True)
            (data / f"{name}.md").write_text("fixture", encoding="utf-8")
            official = policy["effective_limit_overrides"].get(problem_id, {}).get(
                "official_seconds", 1
            )
            problems.append(
                {
                    "id": problem_id,
                    "name": name,
                    "problem_dir": f"data/{name}",
                    "statement_path": f"data/{name}/{name}.md",
                    "time_limit_seconds": official,
                }
            )
        (self.root / "data/coci").mkdir()
        write_json(self.root / "data/coci/problems.json", problems)
        baseline = self.root / "results/judging/baseline"
        baseline.mkdir(parents=True)
        from llm_eval.judging.engine import JUDGE_POLICY
        from llm_eval.judging.workflow import digest

        write_json(
            baseline / "manifest.json",
            {
                "session_id": "baseline",
                "complete": True,
                "judge_sha256": digest(target_judging / "engine.py"),
                "judge_process_sha256": digest(target_judging / "execution.py"),
                "judge_policy": dict(JUDGE_POLICY),
                "test_data": {},
                "entries": [],
            },
        )
        folder = evaluation.prepare_evaluation(self.root, "baseline")
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        self.assertEqual(len(manifest["missing"]), 80)

    def test_repair_revision_is_snapshotted_and_only_identical_completion_skips(self):
        folder = self.prepare()
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with patch.object(evaluation, "judge_problem", return_value=completed_result()), lane:
            evaluation.run_evaluation(self.root, folder.name, "limits")

        repair_path = self.root / "repairs/a.py"
        repair_path.parent.mkdir()
        repair_path.write_text("print(2)\n", encoding="utf-8")
        review_path = folder / "reviews/a/qwen36/round_1/review.json"
        review = read_json(review_path)
        review["repair"] = {
            "decision": "candidate",
            "reason": "fixture repair",
            "algorithm_preserved": True,
            "code_path": str(repair_path.relative_to(self.root)),
        }
        write_json(review_path, review)
        with patch.object(evaluation, "judge_problem", return_value=completed_result("AC")) as mocked, lane:
            evaluation.run_evaluation(self.root, folder.name, "repairs")
            review["explanation"] = {"score": 1, "evidence": "fixture evidence"}
            write_json(review_path, review)
            evaluation.run_evaluation(self.root, folder.name, "repairs")
            repair_path.write_text("print(3)\n", encoding="utf-8")
            evaluation.run_evaluation(self.root, folder.name, "repairs")
        self.assertEqual(mocked.call_count, 2)
        attempts = self.attempts(folder, "repairs")
        self.assertEqual(len(attempts), 2)
        self.assertNotEqual(attempts[0]["candidate_sha256"], attempts[1]["candidate_sha256"])
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        state = evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])
        self.assertEqual(state["current_repair_sha256"], attempts[1]["candidate_sha256"])

    def test_review_allows_pending_but_repair_run_requires_complete_candidate_fields(self):
        folder = self.prepare(status="WA")
        review_path = folder / "reviews/a/qwen36/round_1/review.json"
        review = read_json(review_path)
        review["repair"]["decision"] = "candidate"
        write_json(review_path, review)
        _, manifest = evaluation.load_evaluation(self.root, folder.name)
        state = evaluation.read_entry(self.root, folder, manifest, manifest["entries"][0])
        self.assertIsNone(state["current_repair_sha256"])
        lane = patch.object(
            evaluation, "workload", side_effect=lambda *_args, **_kwargs: contextlib.nullcontext()
        )
        with lane, self.assertRaisesRegex(ValueError, "검토가 미완성"):
            evaluation.run_evaluation(self.root, folder.name, "repairs")


if __name__ == "__main__":
    unittest.main()
