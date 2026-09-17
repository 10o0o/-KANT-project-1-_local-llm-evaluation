# 프로젝트 평가 실행 안내

이 문서는 생성 원본과 기준 `judge batch` 세션이 준비된 뒤 실행하는 오프라인 평가 절차를 설명한다. 평가는 저장소 루트에서 `uv run llm-eval`로 실행하며, 생성 원본·기준 세션·원본 `candidate.py`를 수정하지 않는다. 평가 기준은 생성이 시작된 뒤 확정됐으므로 사전등록된 기준으로 표시하지 않는다. `configs/evaluation.json`의 `decision_phase`는 `during_generation`, `preregistered`는 `false`다.

현재 전체 생성 계획은 네 모델(`qwen36`, `gemma4`, `luna`, `motif3`) × 10문항 × 두 회차 = 80회다. 모델별 분모는 20회이고, 로컬 최소 품질선은 원본 유효 정답 12/20(60%)이다. Luna·Motif-3는 각 20회 분모를 유지하며 최종 로컬 순위에 넣지 않는다. 이전 60회 계획과 당시 35건 관측은 날짜가 있는 이력으로 보존한다. 현재 80회에 속하는 원본 결과를 이전 계획이라는 이유로 pilot으로 분리하지 않는다. 제한 미제공 조건의 별도 pilot은 본 평가에서 제외한다.

## 평가 범위

`judge batch`는 생성 원본을 문제의 공식 1배 시간 제한으로 채점해 기준 세션을 만든다. 평가의 시간 제한 배수는 문제 프롬프트를 바꾸지 않고 오프라인 코드 실행에만 적용한다. 네 scoring 문제의 공식·유효 제한은 다음과 같다.

| 문제 ID | 공식 제한 | 평가 유효 제한 |
| --- | ---: | ---: |
| `coci_2025_2026_c5_tezina` | 2초 | 4초 |
| `coci_2025_2026_c5_pet` | 1초 | 2초 |
| `coci_2025_2026_c6_ucionica` | 1.5초 | 3초 |
| `coci_2025_2026_c6_skijanje` | 1초 | 2초 |

열 문항 모두 공식 1배 제한의 원본 판정과 최소 수정 보조 평가 대상이다. 기준 세션에서 어느 문항이든 개별 테스트에 `TLE`가 있으면 `limits` 실행이 그 문항의 전체 테스트를 2배 제한으로 다시 실행한다. 네 scoring 문항의 2배 결과는 프로젝트 scoring에 반영하고, 나머지 여섯 diagnostic 문항의 2배 결과는 진단으로만 반영한다. 여섯 문항의 공식 1배 원본 판정과 보조 수정 결과는 프로젝트 평가에 포함한다.

기준 세션에서 `AC`인 항목은 `baseline_1x`로 재사용하며 2배 제한 측정으로 표시하지 않는다. 평가 결과의 `source`는 `baseline_1x`, `limit_2x`, `pending_limits` 중 하나다. `pending_limits`, 누락, 아직 확인하지 않은 항목은 0점이나 실패로 바꾸지 않는다.

## 실행 순서

먼저 로컬·Cloud 생성과 로컬 서버 종료를 확인한 뒤 기준 세션을 만든다. 공식 `judge batch` 명령과 채점 정책은 그대로 유지한다.

```bash
uv run llm-eval judge batch --problems all --models all --rounds all
```

기준 세션의 ID를 사용해 평가를 준비한다. `prepare`는 기준 세션이 `complete=true`인 경우 진행하며, `completed_with_missing`는 누락 목록을 기록한 채 준비할 수 있다. 생성 원본과 Judge 엔진·실행 도구의 해시가 정책과 다르면 중단한다.

```bash
uv run llm-eval evaluate prepare --baseline <세션 ID>
```

출력된 평가 ID로 제한 재평가를 실행한다. 이 단계는 개별 테스트의 `TLE`가 있는 열 문항만 대상으로 하며, 완료된 동일 시도는 건너뛴다. 기준 세션의 `AC`를 2배로 다시 재지 않는다.

```bash
uv run llm-eval evaluate run --evaluation <평가 ID> --kind limits
```

`prepare`가 만든 리뷰 파일에 사람이 직접 설명 점수와 보조 수정 판단을 입력한 뒤 보조 수정을 실행한다. 원본 후보 파일은 편집하지 않는다.

```bash
uv run llm-eval evaluate run --evaluation <평가 ID> --kind repairs
```

마지막으로 보고서를 생성한다.

```bash
uv run llm-eval evaluate report --evaluation <평가 ID>
```

`judge candidate`로 별도로 실행한 결과는 이 평가에 자동 편입하지 않는다. 보고서가 만들어졌다는 사실만으로 생성 80회, 후보 채점, 설명 리뷰 또는 최종 모델 선정을 완료한 것으로 표시하지 않는다.

## 리뷰 입력과 집계

평가 산출물은 다음 구조를 사용한다.

```text
results/evaluation/<평가 ID>/
├── manifest.json
├── policy.json
├── reviews/<문제>/<모델>/round_<n>/review.json
├── attempts/<문제>/<모델>/round_<n>/<attempt-id>/
│   ├── attempt.json, attempt.seal
│   ├── candidate.py
│   └── candidate.diff
└── reports/<unique>/
    ├── report.json
    ├── report.md
    └── review-snapshot.json
```

`review.json`의 리뷰 입력은 다음 필드를 유지한다.

```json
{
  "explanation": {"score": null, "evidence": ""},
  "repair": {
    "decision": null,
    "reason": "",
    "algorithm_preserved": null,
    "code_path": null
  }
}
```

설명 점수는 사람이 직접 0·1·2 중 하나를 입력하고 응답 근거를 `evidence`에 적는다. 정상 수신한 `NO_CODE` 응답도 설명 평가에 포함한다. `CALL_ERROR`는 설명 점수에서 제외하고 실패 횟수와 실패 시간 n을 별도로 기록한다. 미입력·미확인 값은 0점으로 채우지 않는다.

보조 수정 판단의 `repair.decision`은 `null`, `not_applicable`, `not_repairable`, `candidate`만 허용한다. `candidate`를 선택할 때는 사유를 적고 `algorithm_preserved=true`와 `code_path`를 함께 입력한다. 보조 수정은 같은 문항의 원본 알고리즘을 유지한 제한 수정만 허용하며, 핵심 알고리즘을 교체하지 않는다. `code_path`는 저장소 루트 기준 상대 경로의 사용자 수정 파일이며 원본 `candidate.py`를 가리키거나 덮어쓰지 않는다. 같은 원본의 완료된 보조 시도는 중복하지 않고, 다른 수정 시도는 새 append-only 기록으로 남긴다. 원본별 보조 통과는 최대 한 번 집계한다.

각 제한·보조 시도는 `attempts/<entry-key>/<attempt-id>/` 아래에 원본과 비교할 `candidate.py`, `candidate.diff`, 입력·정책·판정을 담은 `attempt.json`, 완료 시 `attempt.seal`을 저장한다. 시도와 스냅샷은 기존 benchmark candidate와 별도이며, 보고서는 이 트리를 읽어 집계한다.

성공 호출의 `response_elapsed_seconds`는 코드 유무와 무관하게 평균을 내고 성공 호출 n을 표시한다. `CALL_ERROR`의 실패까지 걸린 시간은 성공 평균에 섞지 않고 실패 시간과 별도 n으로 기록한다. 원본 유효 정답률은 모델별 20회 분모를 유지하며 보조 수정 통과를 포함하지 않는다.

보고서 파일은 평가 산출물과 리뷰 snapshot을 정리하는 JSON·Markdown이다. `report.md`가 최종 실험 보고서의 문장이나 답안을 대신 작성하지 않는다. 최종 선정은 모든 필요한 원본 판정·보조 리뷰·설명 입력과 그 근거를 직접 확인한 뒤 별도로 작성한다.
