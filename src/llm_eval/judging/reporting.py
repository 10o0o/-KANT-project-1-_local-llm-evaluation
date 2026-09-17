"""Deterministic evaluation summaries; never execute or repair a candidate."""

import fcntl
import hashlib
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_eval.shared.storage import write_json, write_text


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def average(values, expected):
    return {"mean": sum(values) / len(values) if values else None,
            "n": len(values), "missing": expected - len(values)}


def valid_answer(result, limit):
    return (result is not None and result.get("status") == "AC"
            and numeric(result.get("max_case_seconds"))
            and result["max_case_seconds"] < limit
            and isinstance(result.get("total_cases"), int)
            and not isinstance(result["total_cases"], bool)
            and result["total_cases"] > 0
            and result.get("passed_cases") == result["total_cases"])


def completed_attempts(state, kind):
    return [a for a in state["attempts"] if a["kind"] == kind
            and a["status"] == "completed" and a.get("result") is not None]


def build_report(manifest, states):
    from llm_eval.judging.evaluation import project_verdict

    policy = manifest["policy"]
    planned = policy["planned_attempts_per_model"]
    models, rows = {}, []
    for model in policy["models"]:
        entries = [e for e in manifest["entries"] if e["model"] == model]
        summary = {
            "planned": planned, "recorded": len(entries), "missing": planned - len(entries),
            "call_success": 0, "call_error": 0, "no_code": 0,
            "baseline_ac": 0, "project_ac": 0, "project_valid": 0,
            "pending_project_verdicts": 0, "judge_errors": 0,
            "verdict_sources": {}, "errors": [],
            "repairs": {"targets": 0, "reviewed": 0, "pending": 0,
                        "attempts": 0, "completed_attempts": 0, "passing_attempts": 0,
                        "unique_passes": 0},
            "diagnostic_2x": {"eligible": 0, "completed": 0, "pending": 0,
                              "ac": 0, "verdicts": {}},
            "scoring_2x": {"eligible": 0, "completed": 0, "pending": 0},
        }
        if summary["missing"] < 0:
            raise ValueError("계획 수보다 많은 원본 항목")
        scores, success_times, failure_times = [], [], []
        source_counts, diag_counts = Counter(), Counter()
        for entry in entries:
            state = states[entry["key"]]
            record, baseline, review = state["record"], state["baseline"], state["review"]
            successful = record["call"]["status"] == "success"
            summary["call_success" if successful else "call_error"] += 1
            if successful and record.get("extracted_code") is None:
                summary["no_code"] += 1
            elapsed = (record.get("metrics") or {}).get("response_elapsed_seconds")
            if numeric(elapsed):
                (success_times if successful else failure_times).append(elapsed)
            explanation = review.get("explanation", {})
            score, evidence = explanation.get("score"), explanation.get("evidence", "")
            if score is not None:
                if type(score) is not int or score not in (0, 1, 2) or not isinstance(evidence, str) or not evidence.strip():
                    raise ValueError(f"설명 점수/근거를 확인하세요: {entry['key']}")
                if not successful:
                    raise ValueError(f"호출 실패는 설명 점수 대상이 아닙니다: {entry['key']}")
                scores.append(score)
            result, source = project_verdict(entry, state)
            source_counts[source] += 1
            summary["baseline_ac"] += baseline.get("status") == "AC"
            summary["project_ac"] += bool(result and result.get("status") == "AC")
            is_valid = valid_answer(result, entry["effective_limit_seconds"])
            summary["project_valid"] += is_valid
            if result is None:
                summary["pending_project_verdicts"] += 1
            elif result.get("status") == "JUDGE_ERROR":
                summary["judge_errors"] += 1
            elif result.get("status") == "AC" and not is_valid:
                summary["errors"].append(f"AC의 실행 시간/테스트 수 확인 필요: {entry['key']}")
            limits = completed_attempts(state, "limits")
            if entry["needs_limit_run"]:
                category = "scoring_2x" if entry["limit_role"] == "scoring" else "diagnostic_2x"
                bucket = summary[category]
                bucket["eligible"] += 1
                bucket["completed"] += bool(limits)
                bucket["pending"] += not bool(limits)
                if category == "diagnostic_2x" and limits:
                    verdict = limits[-1]["result"]["status"]
                    diag_counts[verdict] += 1
                    bucket["ac"] += verdict == "AC"
            repair_target = bool(result and entry.get("candidate_path") and result.get("status")
                                 not in {"AC", "CALL_ERROR", "NO_CODE", "JUDGE_ERROR"})
            repairs = completed_attempts(state, "repairs")
            all_repairs = [a for a in state["attempts"] if a["kind"] == "repairs"]
            passing = [a for a in repairs
                       if a.get("review", {}).get("repair", {}).get("algorithm_preserved") is True
                       and valid_answer(a["result"], entry["effective_limit_seconds"])]
            bucket = summary["repairs"]
            bucket["attempts"] += len(all_repairs)
            bucket["completed_attempts"] += len(repairs)
            bucket["passing_attempts"] += len(passing)
            bucket["unique_passes"] += bool(passing) and repair_target
            repair_reviewed = False
            if repair_target:
                bucket["targets"] += 1
                repair = review.get("repair", {})
                decision, reason = repair.get("decision"), repair.get("reason", "")
                if decision not in (None, "not_applicable", "not_repairable", "candidate"):
                    raise ValueError(f"알 수 없는 수정 검토 값: {entry['key']}")
                reason_present = isinstance(reason, str) and bool(reason.strip())
                if decision == "not_repairable" and reason_present:
                    repair_reviewed = True
                elif decision == "candidate" and reason_present and repair.get("algorithm_preserved") is True:
                    repair_reviewed = any(a.get("candidate_sha256") == state.get("current_repair_sha256")
                                          and state.get("current_repair_sha256") is not None
                                          and a.get("review", {}).get("repair") == repair for a in repairs)
                bucket["reviewed"] += repair_reviewed
                bucket["pending"] += not repair_reviewed
            rows.append({
                "key": entry["key"], "problem_id": entry["problem_id"], "model": model,
                "round": entry["round"], "source_run_id": entry["source_run_id"],
                "official_limit_seconds": entry["official_limit_seconds"],
                "effective_limit_seconds": entry["effective_limit_seconds"],
                "baseline_verdict": baseline.get("status"),
                "project_verdict": result.get("status") if result else None,
                "project_valid": is_valid if result is not None else None,
                "verdict_source": source,
                "diagnostic_verdict": limits[-1]["result"]["status"] if limits and entry["limit_role"] == "diagnostic" else None,
                "explanation_score": score if successful else None,
                "repair_target": repair_target, "repair_reviewed": repair_reviewed,
                "repair_pass": bool(passing) and repair_target,
                "representative_repair": passing[0]["attempt_id"] if passing and repair_target else None,
            })
        summary["verdict_sources"] = dict(source_counts)
        summary["diagnostic_2x"]["verdicts"] = dict(diag_counts)
        summary["explanation"] = {**average(scores, summary["call_success"]),
                                  "expected": summary["call_success"],
                                  "distribution": {str(n): scores.count(n) for n in (0, 1, 2)}}
        summary["success_response_seconds"] = average(success_times, summary["call_success"])
        summary["failure_elapsed_seconds"] = average(failure_times, summary["call_error"])
        summary["project_valid_rate"] = summary["project_valid"] / planned
        summary["originals_complete"] = (summary["missing"] == 0
            and summary["pending_project_verdicts"] == 0 and summary["judge_errors"] == 0
            and not summary["errors"])
        summary["minimum_quality_pass"] = (summary["project_valid"] >= policy["minimum_valid_originals"]
                                            if summary["originals_complete"] and model in policy["local_models"] else None)
        summary["review_complete"] = (summary["originals_complete"]
            and summary["repairs"]["pending"] == 0 and summary["explanation"]["missing"] == 0)
        summary["comparison_ready"] = (summary["review_complete"]
            and summary["success_response_seconds"]["missing"] == 0
            and summary["success_response_seconds"]["n"] > 0)
        models[model] = summary
    local_ready = all(models[m]["comparison_ready"] for m in policy["local_models"])
    ranking = None
    if local_ready:
        def rank_key(m):
            x = models[m]
            return (-x["project_valid"], -x["repairs"]["unique_passes"],
                    -x["explanation"]["mean"], x["success_response_seconds"]["mean"])
        ranking = []
        for model in sorted(policy["local_models"], key=rank_key):
            if ranking and rank_key(model) == rank_key(ranking[-1][0]):
                ranking[-1].append(model)
            else:
                ranking.append([model])
    return {"schema_version": 1, "evaluation_id": manifest["evaluation_id"],
            "policy": policy, "models": models, "entries": rows,
            "complete": all(x["review_complete"] and x["diagnostic_2x"]["pending"] == 0 for x in models.values()),
            "local_comparison_ready": local_ready, "local_metric_order": ranking,
            "selection_note": "지표 비교 순서이며 최종 선정이 아닙니다. License·환경 등 필수 조건과 실제 도입 판단은 직접 확인하세요."}


def render_markdown(report):
    lines = ["# 평가 비교표", "", f"평가 ID: `{report['evaluation_id']}`",
             f"전체 평가 기록 완료: {report['complete']} / 로컬 지표 비교 준비: {report['local_comparison_ready']}",
             "", "미생성·미검토는 실패나 0점이 아닙니다. 미완료 비율은 계획 분모 대비 현재 확인한 값입니다.",
             "", "| 모델 | 기록/계획 | 미생성 | 호출 실패 | NO_CODE | 공식 AC | 프로젝트 AC | 유효 정답/계획 | 2배 진단 AC/대상 | 최소 수정 통과 | 로컬 60% |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for model, x in report["models"].items():
        d = x["diagnostic_2x"]
        lines.append(f"| {model} | {x['recorded']}/{x['planned']} | {x['missing']} | {x['call_error']} | {x['no_code']} | {x['baseline_ac']} | {x['project_ac']} | {x['project_valid']}/{x['planned']} | {d['ac']}/{d['eligible']} | {x['repairs']['unique_passes']} | {x['minimum_quality_pass'] if x['minimum_quality_pass'] is not None else '미확정/비대상'} |")
    lines += ["", "| 모델 | 설명 평균(n) | 설명 미검토 | 성공 응답 평균 초(n) | 시간 누락 | 실패 경과 평균 초(n) | 수정 검토/대상 | 수정 시도 | 2배 미실행 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    def metric(m):
        return f"{m['mean']:.6f} ({m['n']})" if m["mean"] is not None else f"— ({m['n']})"
    for model, x in report["models"].items():
        lines.append(f"| {model} | {metric(x['explanation'])} | {x['explanation']['missing']} | {metric(x['success_response_seconds'])} | {x['success_response_seconds']['missing']} | {metric(x['failure_elapsed_seconds'])} | {x['repairs']['reviewed']}/{x['repairs']['targets']} | {x['repairs']['attempts']} | {x['diagnostic_2x']['pending'] + x['scoring_2x']['pending']} |")
    lines += ["", f"로컬 지표 순서(동률은 같은 묶음): {report['local_metric_order']}", report["selection_note"], "",
              "정책은 생성 진행 중 결정되었습니다. 공식 1배 결과를 보존하며 Tezina·Pet·Ucionica·Skijanje만 평가 제한을 완화합니다.", "",
              "| 원본 항목 | 공식 판정 | 프로젝트 판정 | 근거 | 공식/평가 제한(초) | 2배 진단 | 수정 통과 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in report["entries"]:
        lines.append(f"| {row['key']} | {row['baseline_verdict']} | {row['project_verdict'] or '미실행'} | {row['verdict_source']} | {row['official_limit_seconds']}/{row['effective_limit_seconds']} | {row['diagnostic_verdict'] or '—'} | {row['repair_pass']} |")
    return "\n".join(lines) + "\n"


def report_evaluation(root, evaluation_id):
    from llm_eval.judging.evaluation import load_evaluation, read_entry

    folder, manifest = load_evaluation(root, evaluation_id)
    with (folder / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("평가 작업이 실행 중입니다.") from exc
        states = {e["key"]: read_entry(root, folder, manifest, e) for e in manifest["entries"]}
        report = build_report(manifest, states)
        load_evaluation(root, evaluation_id)
        if states != {e["key"]: read_entry(root, folder, manifest, e) for e in manifest["entries"]}:
            raise ValueError("집계 중 검토 또는 채점 기록이 변경되었습니다.")
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%fZ") + "_" + uuid4().hex[:8]
        destination = folder / "reports" / stamp
        destination.mkdir(parents=True, exist_ok=False)
        report.update(created_at=datetime.now(UTC).isoformat(),
                      reporting_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      manifest_sha256=hashlib.sha256((folder / 'manifest.json').read_bytes()).hexdigest())
        write_json(destination / "review-snapshot.json", {k: s["review"] for k, s in states.items()})
        report["review_snapshot_sha256"] = hashlib.sha256((destination / "review-snapshot.json").read_bytes()).hexdigest()
        report["attempt_ids"] = {k: [a["attempt_id"] for a in s["attempts"]] for k, s in states.items()}
        write_json(destination / "report.json", report)
        write_text(destination / "report.md", render_markdown(report))
        return destination
