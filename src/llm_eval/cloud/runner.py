import json
from datetime import UTC, datetime
from time import perf_counter

from llm_eval.benchmark.prompts import build_round1_prompt
from llm_eval.cloud.client import MODEL, TIMEOUT_SECONDS, request_options
from llm_eval.cloud.metrics import measured_metrics
from llm_eval.code_extract import extract_python_code
from llm_eval.judge import judge_problem


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def completed_record(path, problem, request):
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return False
        if record.get("request") != request:
            raise SystemExit(
                f"ABORT: 기존 Cloud 요청과 현재 입력·설정이 다릅니다: {path}"
            )
        return (
            record["record_complete"] is True
            and record["experiment"]["type"] == "cloud"
            and record["problem"]["id"] == problem["id"]
            and record["model"]["id"] == MODEL
            and record["call"]["status"] in {"success", "error"}
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def run_problem(project_root, problem, client, selected_problem_ids=None):
    result_dir = project_root / "results" / "benchmark" / problem["name"] / "luna" / "round_1"
    result_path = result_dir / "result.json"
    statement = (project_root / problem["statement_path"]).read_text(encoding="utf-8")
    prompt = build_round1_prompt(
        statement,
        time_limit_seconds=problem["time_limit_seconds"],
        memory_limit_mib=problem["memory_limit_mib"],
    )
    request = {**request_options(), "input": [{"role": "user", "content": prompt}]}

    if result_dir.exists():
        if completed_record(result_path, problem, request):
            print(f"SKIP: cloud problem={problem['id']} (이미 기록한 시도)")
            return
        raise SystemExit(f"ABORT: 불완전한 Cloud 결과를 확인하세요: {result_dir}")

    record = {
        "run_id": datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ"),
        "experiment": {"type": "cloud", "round": 1, "planned_attempts": 10},
        "invocation": {"selected_problem_ids": selected_problem_ids or [problem["id"]]},
        "model": {
            "id": MODEL,
            "name": "luna",
            "runtime": "openai_responses",
            "response_model": None,
        },
        "problem": dict(problem),
        "request": request,
        "generation_config": {
            **request_options(),
            "temperature": None,
            "temperature_reason": "Not sent; provider default applies",
        },
        "client_config": {"timeout_seconds": TIMEOUT_SECONDS, "max_retries": 0},
        "call": {"status": None, "error": None},
        "generation": None,
        "metrics": None,
        "extracted_code": None,
        "judge": None,
        "record_complete": False,
    }
    # Exclusive reservation prevents a second invocation from issuing the same paid request.
    result_dir.mkdir(parents=True, exist_ok=False)
    print(f"Cloud 요청: {problem['id']} / {MODEL}")
    start = perf_counter()
    try:
        response = client.responses.create(**request)
    except Exception as exc:
        elapsed = perf_counter() - start
        status_code = getattr(exc, "status_code", None)
        record["call"] = {
            "status": "error",
            "error": {
                "type": type(exc).__name__,
                "status_code": status_code if isinstance(status_code, int) else None,
            },
        }
        record["metrics"] = measured_metrics(elapsed, {})
        record["record_complete"] = True
        write_json(result_path, record)
        # Do not print exception messages, headers or chained traceback containing credentials.
        raise SystemExit(
            f"Cloud 호출 실패: {type(exc).__name__}; 실패 기록 후 중단"
        ) from None
    elapsed = perf_counter() - start
    record["metrics"] = measured_metrics(elapsed, {})
    try:
        data = response.model_dump(mode="json")
        write_json(result_dir / "response.json", data)
        content = response.output_text or ""
        status = data.get("status")
        record["model"]["response_model"] = data.get("model")
        record["call"] = {
            "status": "success" if status in {"completed", "incomplete"} else "error",
            "error": None
            if status in {"completed", "incomplete"}
            else {"type": "ResponseNotCompleted"},
        }
        record["generation"] = {
            "response_id": data.get("id"),
            "status": status,
            "incomplete_details": data.get("incomplete_details"),
            "content": content,
            "reasoning_content": None,
            "reasoning_content_reason": "Internal reasoning is not requested or fabricated",
            "usage": data.get("usage"),
            "service_tier": data.get("service_tier"),
        }
        record["metrics"] = measured_metrics(elapsed, data)
        code = extract_python_code(content)
        record["extracted_code"] = code
        if code is not None:
            candidate = result_dir / "candidate.py"
            candidate.write_text(code, encoding="utf-8")
        if status in {"completed", "incomplete"}:
            if code is None:
                record["judge"] = {
                    "status": "NO_CODE",
                    "passed_cases": 0,
                    "total_cases": None,
                    "max_case_seconds": None,
                    "time_limit_seconds": problem["time_limit_seconds"],
                    "test_results": [],
                }
            else:
                try:
                    record["judge"] = judge_problem(
                        code_path=candidate,
                        problem_dir=project_root / problem["problem_dir"],
                        problem_name=problem["name"],
                        time_limit_seconds=problem["time_limit_seconds"],
                    )
                except Exception as exc:
                    record["judge_error"] = {"type": type(exc).__name__}
                    write_json(result_path, record)
                    raise SystemExit(
                        "Cloud 응답은 보존했습니다. 채점 실패 기록을 확인하세요."
                    ) from None
    except Exception as exc:
        record["processing_error"] = {"type": type(exc).__name__}
        record["record_complete"] = False
        try:
            write_json(result_path, record)
        except OSError:
            pass  # The reserved directory still blocks another paid request.
        raise SystemExit(
            "Cloud 응답 후처리에 실패했습니다. 보존 파일을 확인하세요."
        ) from None
    record["record_complete"] = True
    write_json(result_path, record)
    if record["call"]["status"] == "error":
        raise SystemExit("Cloud 응답의 비정상 상태를 저장하고 중단했습니다.")
    print(
        f"Cloud 완료: {problem['id']} / {status} / {record['judge']['status']} / {elapsed:.2f}s"
    )
