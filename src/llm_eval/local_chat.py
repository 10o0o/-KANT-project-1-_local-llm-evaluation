import json
import logging
from datetime import datetime
from pathlib import Path
from time import perf_counter

from ollama import Client

from llm_eval.utils import (
    chat,
    configure_logging,
    get_metrics_from_response,
    get_vram_info,
    print_result_summary,
    warm_up,
)

MODEL = [
    ("qwen36-35b-lowvram:latest", "qwen36"),
    ("gemma4:26b-a4b-it-q4_K_M", "gemma4"),
]
QUESTION = "프롬프트 엔지니어링이 무엇인지 초보자에게 두 문장으로 설명해 주세요."


def main():
    project_root = Path(__file__).resolve().parents[2]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result_dir = project_root / "results" / run_id
    result_dir.mkdir(parents=True, exist_ok=False)

    # 내 PC에서 실행 중인 Ollama에 연결합니다.
    client = Client(host="http://127.0.0.1:11434", timeout=180)

    configure_logging()

    logger = logging.getLogger(__name__)
    options = {"temperature": 0, "num_predict": 1024, "num_ctx": 4096}

    for model, name in MODEL:
        output_path = result_dir / f"response_{name}.json"

        logger.info("[%s] 워밍업 시작", name)
        elapsed_warm = warm_up(client, model)
        logger.info("[%s] 워밍업 완료 | %.2f초", name, elapsed_warm)

        start = perf_counter()

        try:
            response = chat(client, model, QUESTION, options)
        except Exception as exc:
            elapsed = perf_counter() - start
            logger.error("[%s] 질문 호출 실패: %s", name, type(exc).__name__)
            failure_record = {
                "model": model,
                "question": QUESTION,
                "chat_config": options,
                "status": "error",
                "stage": "question",
                "elapsed_seconds": elapsed,
                "error_type": type(exc).__name__,
                "response": None,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(failure_record, f, ensure_ascii=False, indent=2)

            raise

        elapsed = perf_counter() - start

        (
            tps,
            tps_error_reason,
            load_duration_s,
            load_duration_error_reason,
            prefill_tps,
            prefill_tps_error_reason,
        ) = get_metrics_from_response(response)

        logger.info("[%s] 응답 완료 | %.2f초", name, elapsed)

        vram_mib, vram_error_reason = get_vram_info(client, model)

        with open(output_path, "w", encoding="utf-8") as f:
            record = {
                "question": QUESTION,
                "load_seconds": load_duration_s,
                "load_seconds_error_reason": load_duration_error_reason,
                "elapsed_seconds": elapsed,
                "tps": tps,
                "tps_error_reason": tps_error_reason,
                "prefill_tps": prefill_tps,
                "prefill_tps_error_reason": prefill_tps_error_reason,
                "vram_mib": vram_mib,
                "vram_error_reason": vram_error_reason,
                "chat_config": options,
                "response": response.model_dump(),
            }
            json.dump(record, f, ensure_ascii=False, indent=2)
            # response_JSON = response.model_dump_json(indent=2)
            # f.write(response_JSON)

        with open(output_path, "r", encoding="utf-8") as f:
            saved_response = json.load(f)

        print_result_summary(name, saved_response, output_path)

        client.generate(model=model, prompt="", keep_alive=0)
        logger.info("[%s] 모델 해제 완료", name)
