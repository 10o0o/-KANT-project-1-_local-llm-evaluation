from datetime import UTC, datetime
from time import perf_counter

from llm_eval.cloud.client import (
    MODEL,
    TIMEOUT_SECONDS,
    create_client,
    request_options,
)
from llm_eval.cloud.metrics import measured_metrics
from llm_eval.shared.code_extraction import extract_python_code
from llm_eval.shared.storage import write_json, write_text
from llm_eval.shared.artifacts import (
    generation_complete,
    generation_dir,
    read_generation_record,
    validate_artifacts,
)
from llm_eval.shared.problems import load_problems, problem_prompt, select_problems
from llm_eval.shared.workloads import workload


def completed_record(path, problem, request, round_number=1):
    try:
        record = read_generation_record(path)
        if record.get("request") != request:
            raise SystemExit(
                f"ABORT: 기존 Cloud 요청과 현재 입력·설정이 다릅니다: {path}"
            )
        validate_artifacts(path.parent, record)
        return (
            generation_complete(record)
            and record["experiment"]["type"] == "cloud"
            and record["experiment"]["round"] == round_number
            and record["problem"]["id"] == problem["id"]
            and record["model"]["id"] == MODEL
            and record["call"]["status"] in {"success", "error"}
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def run_problem(
    project_root, problem, client, selected_problem_ids=None, *, round_number=1
):
    if type(round_number) is not int or round_number not in (1, 2):
        raise ValueError(f"잘못된 Cloud 회차: {round_number}; 1 또는 2")
    result_dir = generation_dir(project_root, problem["name"], "luna", round_number)
    result_path = result_dir / "result.json"
    request = request_conditions(project_root, problem)

    if result_dir.exists():
        if completed_record(result_path, problem, request, round_number):
            print(f"SKIP: cloud problem={problem['id']} (이미 기록한 시도)")
            return
        raise SystemExit(f"ABORT: 불완전한 Cloud 결과를 확인하세요: {result_dir}")

    record = build_record(problem, request, selected_problem_ids, round_number)
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
    save_response(result_dir, record, response, elapsed)


def request_conditions(project_root, problem):
    prompt = problem_prompt(project_root, problem)
    return {**request_options(), "input": [{"role": "user", "content": prompt}]}


def build_record(problem, request, selected_problem_ids, round_number=1):
    return {
        "run_id": datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ"),
        "experiment": {
            "type": "cloud", "round": round_number, "planned_attempts": 20,
        },
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


def save_response(result_dir, record, response, elapsed):
    """Preserve received responses separately from transport failures."""
    result_path = result_dir / "result.json"
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
            write_text(candidate, code)
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
        f"Cloud 생성 완료·채점 대기: {record['problem']['id']} / {status} / {elapsed:.2f}s"
    )


def run_selected(project_root, selection: str, round_number: int = 1):
    if type(round_number) is not int or round_number not in (1, 2):
        raise ValueError(f"잘못된 Cloud 회차: {round_number}; 1 또는 2")
    with workload(project_root, "cloud"):
        selected = select_problems(load_problems(project_root), selection)
        if len({problem["id"] for problem in selected}) != len(selected):
            raise ValueError("중복 문제 ID는 허용하지 않습니다.")
        with create_client() as client:
            selected_ids = [problem["id"] for problem in selected]
            for problem in selected:
                run_problem(
                    project_root,
                    problem,
                    client,
                    selected_ids,
                    round_number=round_number,
                )
