import logging
import sys
from time import perf_counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def get_metrics_from_response(response):
    NS_TO_SEC = 1_000_000_000

    duration_ns = response.eval_duration
    token_count = response.eval_count

    tps = None
    tps_error_reason = None

    if duration_ns is None or token_count is None:
        tps_error_reason = "생성 통계 누락"
    elif duration_ns <= 0:
        tps_error_reason = "생성 시간이 0 이하"
    else:
        duration_s = duration_ns / NS_TO_SEC
        tps = token_count / duration_s

    load_duration_ns = response.load_duration
    load_duration_s = None
    load_duration_error_reason = None

    if load_duration_ns is None:
        load_duration_error_reason = "로딩 통계 누락"
    else:
        load_duration_s = load_duration_ns / NS_TO_SEC

    prefill_duration_ns = response.prompt_eval_duration
    prefill_token_count = response.prompt_eval_count

    prefill_tps = None
    prefill_tps_error_reason = None

    if prefill_duration_ns is None or prefill_token_count is None:
        prefill_tps_error_reason = "생성 통계 누락"
    elif prefill_duration_ns <= 0:
        prefill_tps_error_reason = "생성 시간이 0 이하"
    else:
        duration_s = prefill_duration_ns / NS_TO_SEC
        prefill_tps = prefill_token_count / duration_s

    return (
        tps,
        tps_error_reason,
        load_duration_s,
        load_duration_error_reason,
        prefill_tps,
        prefill_tps_error_reason,
    )


def print_result_summary(name, record, output_path):
    console = Console()
    table = Table(title=f"{name} 실행 결과")
    table.add_column("항목")
    table.add_column("값", justify="right")

    table.add_row("전체 응답 시간", f"{record['elapsed_seconds']:.2f}초")

    metrics = [
        ("로딩 시간", "load_seconds", "load_seconds_error_reason", ".3f", "초"),
        ("생성 속도", "tps", "tps_error_reason", ".2f", " tok/s"),
        (
            "입력 처리 속도 (prefill)",
            "prefill_tps",
            "prefill_tps_error_reason",
            ".2f",
            " tok/s",
        ),
        ("모델 VRAM (Ollama 조회)", "vram_mib", "vram_error_reason", ".2f", " MiB"),
    ]
    for label, value_key, reason_key, precision, unit in metrics:
        value = record.get(value_key)
        display = (
            f"{value:{precision}}{unit}"
            if value is not None
            else record.get(reason_key) or "측정값·사유 미기록"
        )
        table.add_row(label, Text(display))

    answer = record["response"]["message"]["content"]
    console.print(Panel(Text(answer), title=f"{name} 답변"))

    console.print(table)
    console.print(f"저장 위치: {output_path}", markup=False)


def warm_up(client, model):
    warm_start = perf_counter()
    client.generate(
        model=model,
        prompt="",
        keep_alive="10m",
    )
    return perf_counter() - warm_start


def chat(client, model, QUESTION, options):
    return client.chat(
        model=model,
        messages=[{"role": "user", "content": QUESTION}],
        stream=False,
        keep_alive="10m",
        options=options,
    )


def get_vram_info(client, model):
    try:
        running_models = client.ps()
    except Exception as exc:
        return None, f"VRAM 조회 실패 ({type(exc).__name__})"

    current_model = None

    for loaded_model in running_models.models:
        if loaded_model.model == model:
            current_model = loaded_model
            break

    vram_mib = None
    vram_error_reason = None

    if current_model is None:
        vram_error_reason = "실행 모델 조회 안됨"
    elif current_model.size_vram is None:
        vram_error_reason = "VRAM 통계 누락"
    else:
        vram_mib = current_model.size_vram / 1024**2

    return vram_mib, vram_error_reason
