"""One command tree for generation, diagnostics and offline judging."""

import argparse
import tomllib
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="llm-eval", description="LLM 생성·기록·별도 채점"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="선택한 문제의 응답과 후보 저장")
    providers = generate.add_subparsers(dest="provider", required=True)
    local = providers.add_parser("local", help="실행 중인 로컬 서버에 요청")
    local.add_argument("--model", choices=("qwen36", "gemma4"), required=True)
    local.add_argument(
        "--problems", required=True, help="all 또는 쉼표로 구분한 문제 ID"
    )
    local.add_argument("--round", type=int, choices=(1, 2), required=True)
    cloud = providers.add_parser("cloud", help="Luna에 독립 요청")
    cloud.add_argument(
        "--problems", required=True, help="all 또는 쉼표로 구분한 문제 ID"
    )
    cloud.add_argument("--round", type=int, choices=(1, 2), default=1)
    queue = commands.add_parser("queue", help="Qwen·Gemma 서버와 두 회차를 순차 진행")
    queue.add_argument("--startup-timeout-seconds", type=float, default=900)
    warmup = commands.add_parser("warmup", help="로컬 워밍업; 본 실험 기록에서 제외")
    warmup.add_argument("--model", choices=("qwen36", "gemma4"), required=True)
    judge = commands.add_parser("judge", help="모든 생성과 서버 종료 후 채점")
    modes = judge.add_subparsers(dest="mode", required=True)
    batch = modes.add_parser("batch", help="저장된 원본 후보를 새 세션에서 채점")
    batch.add_argument("--problems", default="all")
    batch.add_argument("--models", default="all")
    batch.add_argument("--rounds", default="all")
    candidate = modes.add_parser("candidate", help="지정한 수정 후보 확인")
    candidate.add_argument("--code", type=Path, required=True)
    candidate.add_argument("--problem", required=True)
    commands.add_parser("validate", help="문제 목록·문제문·테스트 파일 검증")
    diagnose = commands.add_parser("diagnose", help="본 실험과 분리한 로컬 진단")
    probes = diagnose.add_subparsers(dest="probe", required=True)
    probes.add_parser("response", help="기존 Gemma 응답 진단")
    limit = probes.add_parser(
        "generation-limit", help="기존 고정 문제의 출력 한도 진단"
    )
    limit.add_argument("--model", choices=("qwen36", "gemma4"), required=True)
    return parser.parse_args(argv)


def project_root():
    """Require the selected checkout, never infer it from an installed package."""
    root = Path.cwd().resolve()
    try:
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        valid = metadata.get("project", {}).get("name") == "local-llm-evaluation"
        valid = valid and (root / "src/llm_eval").is_dir()
        valid = valid and (root / "data/coci/problems.json").is_file()
    except (OSError, ValueError):
        valid = False
    if not valid:
        raise ValueError("local-llm-evaluation 저장소 루트에서 실행하세요.")
    return root


def dispatch(root, args):
    if args.command == "generate":
        if args.provider == "local":
            from llm_eval.local.generation import run_selected

            return run_selected(root, args.model, args.problems, args.round)
        from llm_eval.cloud.generation import run_selected

        return run_selected(root, args.problems, args.round)
    if args.command == "queue":
        from llm_eval.local.queue import run_queue

        return run_queue(root, args.startup_timeout_seconds)
    if args.command == "warmup":
        from llm_eval.local.client import run_warmup

        return run_warmup(root, args.model)
    if args.command == "judge":
        from llm_eval.judging.workflow import run_batch_judging, run_candidate_check

        if args.mode == "batch":
            return run_batch_judging(root, args.problems, args.models, args.rounds)
        return run_candidate_check(root, args.code, args.problem)
    if args.command == "diagnose":
        from llm_eval.diagnostics import run_generation_limit_probe, run_response_probe

        if args.probe == "response":
            return run_response_probe(root)
        return run_generation_limit_probe(root, args.model)
    from llm_eval.shared.problems import validate_dataset

    messages, errors = validate_dataset(root)
    for message in messages:
        print(message)
    if errors:
        print("\nValidation FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Validation PASSED")


def main(argv=None):
    args = parse_args(argv)
    try:
        dispatch(project_root(), args)
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"ABORT: {exc}") from None
