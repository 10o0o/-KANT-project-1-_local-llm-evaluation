import contextlib
import io
import json
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from llm_eval import runtime, server_session
from llm_eval.benchmark import runner, warmup
from llm_eval.llama_cpp import chat


class RuntimeTests(unittest.TestCase):
    def test_request_disables_prompt_cache(self):
        client = Mock()
        chat(client, "qwen36", "example")
        request = client.chat.completions.create.call_args.kwargs
        self.assertIs(request["extra_body"]["cache_prompt"], False)

    def test_metrics_missing_invalid_and_zero(self):
        for timings in (
            {},
            {"predicted_ms": 0, "predicted_per_second": 10},
            {"predicted_ms": -1, "predicted_per_second": 10},
            {"predicted_ms": 1, "predicted_per_second": float("nan")},
        ):
            metrics = runtime.measured_metrics(2, {}, timings, {})
            self.assertIsNone(metrics["generation_tokens_per_second"])
            self.assertTrue(metrics["generation_tokens_per_second_reason"])
        metrics = runtime.measured_metrics(
            2,
            {"completion_tokens": 0},
            {"predicted_ms": 10, "predicted_per_second": 0},
            {},
        )
        self.assertEqual(metrics["generation_tokens_per_second"], 0)
        self.assertIsNone(metrics["generation_tokens_per_second_reason"])
        self.assertEqual(metrics["completion_tokens"], 0)
        self.assertIsNone(metrics["model_load_seconds"])
        self.assertTrue(metrics["model_load_reason"])

    @patch("llm_eval.runtime.command_output")
    def test_process_memory_does_not_fall_back_to_device(self, command):
        command.side_effect = ["GPU-1, Test GPU, 4000, 8000", "123, GPU-1, [N/A]"]
        memory = runtime.observe_memory(123, "response_received")
        self.assertEqual(memory["devices"]["value"][0]["used_mib"], 4000)
        self.assertIsNone(memory["process"]["value"])
        self.assertTrue(memory["process"]["reason"])

    @patch("llm_eval.runtime.command_output")
    def test_memory_matches_only_server_pid(self, command):
        command.side_effect = [
            "GPU-1, Test GPU, 4000, 8000",
            "123, GPU-1, 512\n999, GPU-1, 2048",
        ]
        self.assertEqual(
            runtime.observe_memory(123, "server_ready")["process"]["value"], 512
        )

    @patch("llm_eval.runtime.command_output")
    def test_invalid_memory_is_missing_not_negative_or_nan(self, command):
        for value in ("-1", "nan", "[N/A]"):
            with self.subTest(value=value):
                command.side_effect = [
                    "GPU-1, Test GPU, 4000, 8000",
                    f"123, GPU-1, {value}",
                ]
                observed = runtime.observe_memory(123, "response_received")
                self.assertIsNone(observed["process"]["value"])
                self.assertTrue(observed["process"]["reason"])

    @patch("llm_eval.runtime.observe_memory", side_effect=RuntimeError("probe failed"))
    def test_observation_failure_is_data(self, _):
        self.assertIsNone(runtime.safe_memory(123, "call_error")["process"]["value"])

    @patch("llm_eval.runtime.get_json")
    @patch("llm_eval.runtime.owns_server_port", return_value=True)
    @patch("llm_eval.runtime.process_identity")
    def test_session_binding_rejects_stale_pid_and_changed_props(
        self, identity, owns, get_json
    ):
        proc = {
            "pid": 123,
            "start_ticks": "1",
            "boot_id": "boot",
            "executable": "/server",
        }
        props = {
            "model_path": "/model.gguf",
            "default_generation_settings": {"n_ctx": 12288},
            "total_slots": 1,
        }
        env = {
            "data": {
                "model": "qwen36",
                "process": proc,
                "artifacts": {},
                "observed": {"props": runtime.props_identity(props)},
            }
        }
        identity.return_value = dict(proc, start_ticks="2")
        with self.assertRaisesRegex(ValueError, "identity"):
            runtime.validate_environment(env, "qwen36")
        get_json.assert_not_called()
        identity.return_value = proc
        get_json.side_effect = [{"status": "ok"}, props, {"data": [{"id": "qwen36"}]}]
        runtime.validate_environment(env, "qwen36")
        get_json.side_effect = [{"status": "ok"}, dict(props, total_slots=2)]
        with self.assertRaisesRegex(ValueError, "properties"):
            runtime.validate_environment(env, "qwen36")
        owns.return_value = False
        with self.assertRaisesRegex(ValueError, "port"):
            runtime.validate_environment(env, "qwen36")

    @patch("llm_eval.runtime.command_output", side_effect=["source-commit", ""])
    @patch("llm_eval.runtime.owns_server_port", return_value=True)
    @patch("llm_eval.runtime.process_identity")
    @patch("llm_eval.runtime.process_arguments")
    @patch("llm_eval.runtime.get_json")
    def test_capture_keeps_configured_and_observed_separate(
        self, get_json, arguments, identity, owns, command
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "build/bin/llama-server"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"mock binary")
            model = root / "model.gguf"
            model.write_bytes(b"mock model")
            log = root / "server.log"
            log.write_text(
                "print_info: file type = Q4_K - Medium\nload_tensors: offloaded 12/33 layers to GPU\n"
            )
            arguments.return_value = [
                str(binary),
                "--model",
                str(model),
                "--alias",
                "qwen36",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "--ctx-size",
                "12288",
                "--gpu-layers",
                "all",
            ]
            identity.return_value = {"pid": 123, "executable": str(binary)}
            props = {
                "model_path": str(model),
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 8192},
                "build_info": "binary-build",
            }
            get_json.side_effect = [props, {"data": [{"id": "qwen36"}]}]
            env = runtime.capture_environment(123, "qwen36", "session", log, 3.5, {})
            self.assertEqual(env["configured"]["arguments"]["--ctx-size"], "12288")
            self.assertEqual(env["observed"]["context_size"]["value"], 8192)
            self.assertEqual(env["observed"]["raw_props"], props)
            self.assertEqual(
                env["observed"]["gpu_offload"]["value"], "12/33 layers to GPU"
            )
            self.assertEqual(env["observed"]["quantization"]["value"], "Q4_K - Medium")
            self.assertEqual(env["artifacts"]["model"]["sha256"], runtime.sha256(model))
            self.assertEqual(env["source_checkout"]["root"], str(root))
            self.assertEqual(env["observed"]["server_startup_seconds"], 3.5)

    @patch("llm_eval.runtime.validate_environment")
    def test_manifest_reference_hash_and_wrong_model(self, validate):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "environment.json"
            data = {
                "schema_version": 1,
                "status": "ready",
                "model": "qwen36",
                "session_id": "session",
                "server_url": runtime.SERVER_URL,
                "observed": {"server_startup_seconds": 2},
            }
            path.write_text(json.dumps(data))
            env = runtime.load_environment(path, "qwen36", root)
            self.assertEqual(env["reference"]["sha256"], runtime.sha256(path))
            self.assertEqual(env["reference"]["path"], "environment.json")
            with self.assertRaises(ValueError):
                runtime.load_environment(path, "gemma4", root)


class LauncherTests(unittest.TestCase):
    @patch("llm_eval.server_session.owns_server_port", return_value=True)
    @patch("llm_eval.server_session.get_json", return_value={"status": "ok"})
    @patch("llm_eval.server_session.time.perf_counter", side_effect=[10.2, 10.3])
    def test_ready_time(self, clock, get_json, owns):
        process = Mock(pid=123)
        process.poll.return_value = None
        self.assertAlmostEqual(server_session.wait_ready(process, 10, 600), 0.3)

    @patch("llm_eval.server_session.get_json")
    def test_early_exit_does_not_accept_other_server(self, get_json):
        process = Mock(returncode=1)
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "exited"):
            server_session.wait_ready(process, 0, 600)
        get_json.assert_not_called()

    @patch("llm_eval.server_session.time.perf_counter", return_value=601)
    def test_timeout(self, _):
        process = Mock()
        process.poll.return_value = None
        with self.assertRaises(TimeoutError):
            server_session.wait_ready(process, 0, 600)

    @patch("llm_eval.server_session.os.killpg")
    def test_cleanup_only_owned_group(self, kill):
        process = Mock(pid=123)
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("owned", 10), 0]
        server_session.stop_owned(process)
        self.assertEqual(kill.call_args_list[0].args, (123, signal.SIGTERM))
        self.assertEqual(kill.call_args_list[1].args, (123, signal.SIGKILL))
        process.poll.return_value = 0
        kill.reset_mock()
        server_session.stop_owned(process)
        kill.assert_not_called()

    def test_manifest_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "environment.json"
            server_session.write_record(path, {"status": "ready"})
            with self.assertRaises(FileExistsError):
                server_session.write_record(path, {"status": "changed"})
            self.assertEqual(json.loads(path.read_text())["status"], "ready")

    @patch("llm_eval.server_session.subprocess.Popen")
    @patch("llm_eval.server_session.port_in_use", return_value=True)
    def test_occupied_port_no_spawn(self, _, popen):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "already"):
                server_session.start_model(Path(tmp), "qwen36")
            popen.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    @patch("llm_eval.server_session.stop_owned")
    @patch("llm_eval.server_session.capture_environment")
    @patch("llm_eval.server_session.safe_memory", return_value={})
    @patch("llm_eval.server_session.wait_ready", return_value=2.5)
    @patch("llm_eval.server_session.subprocess.Popen")
    @patch("llm_eval.server_session.port_in_use", return_value=False)
    def test_ready_manifest_survives_exit_and_interrupt(
        self, _, popen, ready, memory, capture, stop
    ):
        for interrupted in (False, True):
            process = popen.return_value
            process.poll.return_value = None
            process.returncode = 0
            process.wait.side_effect = KeyboardInterrupt() if interrupted else None
            process.wait.return_value = 0
            capture.return_value = {
                "status": "ready",
                "observed": {"server_startup_seconds": 2.5},
            }
            with (
                self.subTest(interrupted=interrupted),
                tempfile.TemporaryDirectory() as tmp,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                root = Path(tmp)
                result = server_session.start_model(root, "qwen36")
                self.assertEqual(result, 130 if interrupted else 0)
                env_path = next(root.glob("results/environment/*/environment.json"))
                self.assertEqual(json.loads(env_path.read_text()), capture.return_value)
                self.assertEqual(
                    json.loads(env_path.with_name("exit.json").read_text())[
                        "exit_code"
                    ],
                    result,
                )
                self.assertEqual(capture.call_args.args[4], 2.5)
                stop.assert_called_with(process, signal.SIGTERM)

    @patch("llm_eval.server_session.stop_owned")
    @patch("llm_eval.server_session.wait_ready", side_effect=TimeoutError("deadline"))
    @patch("llm_eval.server_session.subprocess.Popen")
    @patch("llm_eval.server_session.port_in_use", return_value=False)
    def test_startup_failure_preserved(self, _, popen, ready, stop):
        popen.return_value.returncode = None
        with (
            tempfile.TemporaryDirectory() as tmp,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            root = Path(tmp)
            self.assertEqual(server_session.start_model(root, "qwen36"), 1)
            path = next(root.glob("results/environment/*/environment.json"))
            self.assertEqual(json.loads(path.read_text())["status"], "failed")
            self.assertTrue(path.with_name("server.log").exists())
            stop.assert_called_once()


class RunRecordTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "data": {"process": {"pid": 123}},
            "reference": {
                "session_id": "session",
                "path": "environment.json",
                "sha256": "abc",
                "server_startup_seconds": 1,
            },
        }
        self.problem = {
            "id": "p",
            "name": "p",
            "title": "P",
            "difficulty": 1,
            "time_limit_seconds": 1,
            "memory_limit_mib": 512,
            "judge_type": "token",
            "problem_dir": "tests",
            "statement_path": "statement.md",
        }
        self.response = Mock()
        self.response.model_dump.return_value = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "No code", "reasoning_content": ""},
                }
            ],
            "usage": {"completion_tokens": 0},
            "timings": {"predicted_ms": 1, "predicted_per_second": 0},
        }

    def test_success_and_failure_records_for_both_paths(self):
        for module, kind in ((runner, "benchmark"), (warmup, "warmup")):
            for failed in (False, True):
                with (
                    self.subTest(kind=kind, failed=failed),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    root = Path(tmp)
                    (root / "statement.md").write_text("Example statement")
                    with (
                        patch.object(module, "validate_environment"),
                        patch.object(
                            module,
                            "chat",
                            side_effect=RuntimeError("offline") if failed else None,
                            return_value=self.response,
                        ),
                        patch(
                            "llm_eval.runtime.observe_memory",
                            side_effect=RuntimeError("unsupported"),
                        ),
                        contextlib.redirect_stdout(io.StringIO()),
                    ):

                        def run(module=module, root=root):
                            if module is runner:
                                runner.run_problem(
                                    root, self.problem, "qwen36", 1, Mock(), self.env
                                )
                            else:
                                warmup.run_warmup(root, "qwen36", Mock(), self.env)

                        if failed:
                            with self.assertRaisesRegex(RuntimeError, "offline"):
                                run()
                        else:
                            run()
                    path = next((root / "results").rglob("result.json"))
                    record = json.loads(path.read_text())
                    self.assertEqual(record["experiment"]["type"], kind)
                    self.assertEqual(
                        record["call"]["status"], "error" if failed else "success"
                    )
                    self.assertIs(record["generation_config"]["cache_prompt"], False)
                    self.assertEqual(record["environment"], self.env["reference"])
                    self.assertIsNone(record["metrics"]["memory"]["process"]["value"])
                    self.assertTrue(record["metrics"]["model_load_reason"])
                    if not failed:
                        self.assertEqual(
                            record["metrics"]["generation_tokens_per_second"], 0
                        )
                        self.assertTrue(path.with_name("response.json").exists())
                    if module is runner:
                        self.assertIn("judge", record)
                        self.assertIn("extracted_code", record)

    def test_raw_response_is_saved_before_memory_probe(self):
        for module in (runner, warmup):
            with (
                self.subTest(module=module.__name__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                (root / "statement.md").write_text("Example")

                def interrupted_probe(pid, phase, root=root):
                    response = next(root.glob("results/**/response.json"))
                    self.assertEqual(
                        json.loads(response.read_text()),
                        self.response.model_dump.return_value,
                    )
                    raise KeyboardInterrupt

                with (
                    patch.object(module, "validate_environment"),
                    patch.object(module, "chat", return_value=self.response),
                    patch.object(module, "safe_memory", side_effect=interrupted_probe),
                    contextlib.redirect_stdout(io.StringIO()),
                    self.assertRaises(KeyboardInterrupt),
                ):
                    if module is runner:
                        runner.run_problem(
                            root, self.problem, "qwen36", 1, Mock(), self.env
                        )
                    else:
                        warmup.run_warmup(root, "qwen36", Mock(), self.env)

    @patch("llm_eval.benchmark.runner.chat")
    @patch(
        "llm_eval.benchmark.runner.validate_environment",
        side_effect=ValueError("wrong session"),
    )
    def test_invalid_session_before_model_attempt(self, _, chat_mock):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "wrong session"):
                runner.run_problem(root, self.problem, "qwen36", 1, Mock(), self.env)
            chat_mock.assert_not_called()
            self.assertFalse((root / "results").exists())


if __name__ == "__main__":
    unittest.main()
