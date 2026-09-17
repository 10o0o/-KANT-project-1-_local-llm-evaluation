import contextlib
import fcntl
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_eval.judging import workflow as batch
from llm_eval.shared.storage import write_json


class BatchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.idle = self.enterContext(patch.object(batch, "active_workloads", return_value=[]))
        self.judge = self.enterContext(patch.object(batch, "judge_problem", return_value={
            "status": "AC", "passed_cases": 1, "total_cases": 1,
            "max_case_seconds": 0.1, "time_limit_seconds": 1, "test_results": [],
        }))
        self.problems = [{"id": f"id_{name}", "name": name, "problem_dir": f"data/{name}",
                          "time_limit_seconds": 1, "judge_type": "token"} for name in ("a", "b")]
        (self.root / "data/coci").mkdir(parents=True)
        write_json(self.root / "data/coci/problems.json", self.problems)
        for problem in self.problems:
            folder = self.root / problem["problem_dir"]
            folder.mkdir()
            (folder / f"{problem['name']}.in.1").write_text("1")
            (folder / f"{problem['name']}.out.1").write_text("1")

    def source(self, name="a", model="qwen36", number=1, code="print(1)", legacy=False, error=False):
        folder = self.root / f"results/benchmark/{name}/{model}/round_{number}"
        folder.mkdir(parents=True)
        record = {
            "run_id": f"run-{name}-{model}-{number}",
            "problem": {"id": f"id_{name}", "time_limit_seconds": 1},
            "model": {"id": batch.MODEL_IDS[model]},
            "experiment": {"type": "cloud" if model == "luna" else "benchmark", "round": number},
            "call": {"status": "error" if error else "success"},
            "generation": None if error else {"content": code or "no code"},
            "extracted_code": code, "judge": {"status": "TLE"} if legacy else None,
        }
        if not legacy or model == "luna":
            record["record_complete"] = True
        write_json(folder / "result.json", record)
        if not error:
            write_json(folder / "response.json", {"raw": "response"})
            if code is not None:
                (folder / "candidate.py").write_text(code)
        return folder

    def manifest(self, session):
        return json.loads((session / "manifest.json").read_text())

    def snapshot(self):
        return {str(p): p.read_bytes() for p in (self.root / "results/benchmark").rglob("*") if p.is_file()}

    def test_old_and_new_sources_sequential_immutable_and_sessions_preserved(self):
        a = self.source(legacy=True)
        b = self.source("b", "luna")
        before = self.snapshot()
        first = batch._run_batch(self.root)
        manifest = self.manifest(first)
        self.assertTrue(manifest["complete"])
        self.assertFalse(manifest["coverage_complete"])
        self.assertEqual(manifest["status"], "completed_with_missing")
        self.assertEqual([c.kwargs["code_path"] for c in self.judge.call_args_list], [a / "candidate.py", b / "candidate.py"])
        self.assertEqual(self.snapshot(), before)
        saved = {str(p): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        second = batch._run_batch(self.root)
        self.assertNotEqual(first, second)
        self.assertEqual(saved, {str(p): p.read_bytes() for p in first.rglob("*") if p.is_file()})
        self.assertEqual(self.judge.call_count, 4)
        entry = manifest["entries"][0]
        result = json.loads((first / entry["judge_path"]).read_text())
        self.assertEqual(result["candidate_sha256"], batch.digest(a / "candidate.py"))
        self.assertEqual(result["source_run_id"], "run-a-qwen36-1")
        self.assertTrue(manifest["test_data"]["id_a"])
        self.assertTrue(manifest["missing"])
        self.assertTrue(any("luna/round_2" in x for x in manifest["missing"]))

    def test_concurrent_batch_lock_prevents_execution(self):
        self.source()
        folder = self.root / "results/judging"
        folder.mkdir()
        with (folder / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, "다른 일괄 채점"):
                batch._run_batch(self.root)
        self.judge.assert_not_called()

    def test_invalid_identity_or_missing_generation_blocks(self):
        folder = self.source()
        path = folder / "result.json"
        original = json.loads(path.read_text())
        for key, value in [("model", {"id": "gemma4"}),
                           ("problem", {"id": "id_a", "time_limit_seconds": 2}),
                           ("generation", None)]:
            saved = {**original, key: value}
            write_json(path, saved)
            with self.assertRaises(ValueError):
                batch._run_batch(self.root)
        self.judge.assert_not_called()

    def test_no_code_and_call_error_are_distinct_and_never_execute(self):
        self.source(code=None)
        self.source("b", error=True, code=None)
        session = batch._run_batch(self.root)
        entries = self.manifest(session)["entries"]
        self.assertEqual([e["status"] for e in entries], ["NO_CODE", "CALL_ERROR"])
        self.assertIsNone(entries[1]["judge_path"])
        self.judge.assert_not_called()

    def test_selection_uses_full_problem_id_model_and_round(self):
        self.source()
        self.source("b", "gemma4", 2)
        session = batch._run_batch(self.root, "id_b", "gemma4", "2")
        self.assertEqual(len(self.manifest(session)["entries"]), 1)
        self.assertEqual(self.judge.call_args.kwargs["problem_name"], "b")
        with self.assertRaises(ValueError):
            batch._run_batch(self.root, "b")

    def test_manifest_identifies_actual_engine(self):
        self.source()
        session = batch._run_batch(self.root)
        implementation = Path(batch.__file__).with_name("engine.py")
        process = Path(batch.__file__).with_name("execution.py")
        manifest = self.manifest(session)
        self.assertEqual(manifest["judge_sha256"], batch.digest(implementation))
        self.assertEqual(manifest["judge_process_sha256"], batch.digest(process))
        self.assertEqual(
            manifest["judge_policy"],
            {
                "version": 1,
                "per_test_output_limit_bytes": 10 * 1024 * 1024,
                "output_limit_scope": "combined_stdout_stderr_bytes",
                "resource_verdict_precedence": "first_trigger",
            },
        )

    def test_incomplete_or_modified_sources_abort_before_any_judging(self):
        self.source()
        folder = self.source("b")
        candidate = folder / "candidate.py"
        candidate.write_text("changed")
        with self.assertRaisesRegex(ValueError, "원본 extracted_code"):
            batch._run_batch(self.root)
        candidate.write_text("print(1)")
        (folder / "result.json").unlink()
        with self.assertRaisesRegex(ValueError, "불완전"):
            batch._run_batch(self.root)
        self.judge.assert_not_called()
        self.assertFalse(list((self.root / "results/judging").glob("*/manifest.json")))

    def test_missing_candidate_raw_or_test_output_aborts(self):
        folder = self.source()
        for path in [folder / "candidate.py", folder / "response.json", self.root / "data/a/a.out.1"]:
            content = path.read_bytes()
            path.unlink()
            with self.assertRaises(ValueError):
                batch._run_batch(self.root)
            path.write_bytes(content)
        self.judge.assert_not_called()

    def test_live_workload_blocks_without_session_or_execution(self):
        self.source()
        self.idle.return_value = [{"pid": 123, "name": "llama-server"}]
        with self.assertRaisesRegex(RuntimeError, "실행 중"):
            batch._run_batch(self.root)
        self.assertFalse((self.root / "results/judging").exists())
        self.judge.assert_not_called()

    def test_interrupt_and_error_preserve_finished_result(self):
        self.source()
        self.source("b")
        for failure, status in [(KeyboardInterrupt(), "interrupted"), (OSError("fixture"), "error")]:
            good = {"status": "AC", "test_results": []}
            self.judge.side_effect = [good, failure]
            with self.assertRaises(type(failure)):
                batch._run_batch(self.root)
            manifests = sorted((self.root / "results/judging").glob("*/manifest.json"))
            path = manifests[-1]
            data = json.loads(path.read_text())
            self.assertFalse(data["complete"])
            self.assertEqual(data["status"], status)
            self.assertTrue((path.parent / data["entries"][0]["judge_path"]).exists())
            self.assertEqual(data["entries"][1]["status"], "JUDGE_ERROR")

    def test_candidate_change_during_judge_marks_session_failed(self):
        folder = self.source()
        def change(**kwargs):
            (folder / "candidate.py").write_text("modified")
            return {"status": "AC"}
        self.judge.side_effect = change
        with self.assertRaisesRegex(ValueError, "후보 코드 변경"):
            batch._run_batch(self.root)
        path = next((self.root / "results/judging").glob("*/manifest.json"))
        self.assertFalse(json.loads(path.read_text())["complete"])

    def test_false_completion_marker_does_not_accept_legacy_judge(self):
        folder = self.source(legacy=True)
        path = folder / "result.json"
        record = json.loads(path.read_text())
        record["record_complete"] = False
        write_json(path, record)
        with self.assertRaises(ValueError):
            batch._run_batch(self.root)
        self.judge.assert_not_called()

    def test_coverage_counts_include_both_luna_rounds(self):
        names = [f"p{number}" for number in range(10)]
        problems = [
            {"id": f"id_{name}", "name": name, "problem_dir": f"data/{name}",
             "time_limit_seconds": 1, "judge_type": "token"}
            for name in names
        ]
        write_json(self.root / "data/coci/problems.json", problems)
        for problem in problems:
            folder = self.root / problem["problem_dir"]
            folder.mkdir()
            (folder / f"{problem['name']}.in.1").write_text("1")
            (folder / f"{problem['name']}.out.1").write_text("1")
        for name in names:
            for model in batch.MODEL_IDS:
                for number in (1, 2):
                    self.source(name, model, number)

        all_entries, all_missing, _ = batch.collect(
            self.root, problems, list(batch.MODEL_IDS), ["1", "2"]
        )
        luna_entries, luna_missing, _ = batch.collect(
            self.root, problems, ["luna"], ["1", "2"]
        )
        luna_round_one, luna_round_one_missing, _ = batch.collect(
            self.root, problems, ["luna"], ["1"]
        )
        luna_round_two, luna_round_two_missing, _ = batch.collect(
            self.root, problems, ["luna"], ["2"]
        )

        self.assertEqual((len(all_entries), len(all_missing)), (60, 0))
        self.assertEqual((len(luna_entries), len(luna_missing)), (20, 0))
        self.assertEqual((len(luna_round_one), len(luna_round_one_missing)), (10, 0))
        self.assertEqual((len(luna_round_two), len(luna_round_two_missing)), (10, 0))
