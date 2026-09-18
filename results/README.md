# 실행 결과

실행은 저장소 루트의 `uv run llm-eval`을 사용한다. 이 문서는 생성 파일군의 이름·소유 책임·집계 경계만 설명하며, 실제 응답·후보 코드·로그 내용은 여기에 복사하지 않는다. 원본 생성은 local/cloud generation이, 오프라인 판정은 judging workflow가 소유한다.

| 경로 | 용도 | 본 실험 집계 |
| --- | --- | --- |
| `benchmark/<문제>/luna/round_<회차>/` | Cloud Luna 10문항×2회 독립 실행(총 20회), 로컬과 별도 비교 | Luna 집계 |
| `benchmark/<문제>/motif3/round_<회차>/` | Cloud Motif-3 10문항×2회 독립 실행(총 20회), 두 번째 Cloud 비교 대상 | Motif-3 집계 |
| `benchmark/<문제>/<qwen36 또는 gemma4>/round_<회차>/` | 로컬 모델당 10문항×2회 | 로컬 집계 |
| `evaluation/<평가 ID>/` | 기준 채점 세션에 연결한 제한 재평가·보조 수정·설명 리뷰·보고서 | 평가 집계; benchmark 원본과 분리 |
| `pilot/pre_offline_judging_20260916_173157_900249/` | 생성·일괄 채점 분리 후 새 실행을 위한 기존 19건·54파일 원본 보존 | 제외 |
| `pilot/pre_resource_limits_20260916_162603_416706/` | 실행 제한 미제공 조건의 로컬 6회·Cloud 10회와 이동 manifest | 제외 |
| `pilot/reasoning_block/` | Reasoning 종료 메시지 추가 후 Tomahawk 진단 | 제외 |
| [pilot/6144](pilot/6144/) | 출력 한도 6144에서 중단한 초기 benchmark 8회 | 제외 |
| [calibration/stress](calibration/stress/) | 생성 한도 결정용 스트레스 실행 | 제외 |
| [diagnostics/struktura](diagnostics/struktura/) | WA 원인을 확인하기 위한 수동 코드 수정본 | 제외 |
| [diagnostics/llama-cpp-startup](diagnostics/llama-cpp-startup/) | 2026-09-16 Qwen 적재·Context 조정 시작 로그 7건 | 제외 |
| [archive/legacy-runs](archive/legacy-runs/) | 초기 연결·Ollama 실습·benchmark 개발 과정의 timestamp 결과 | 제외 |

AI의 원본 조회에서 확인한 중단 기록은 Qwen 20건·Luna 10건·Gemma Round 1 5건, 합계 35건이며 호출 상태는 모두 성공이다. Qwen의 `skijanje` 2건은 코드 미추출이며 실제 후보 채점은 하지 않았다. 이는 당시 로컬 40회·Cloud 20회, 총 60회 계획의 완료나 Judge 실행 완료를 뜻하지 않는다. 현재 전체 계획은 로컬 40회와 Cloud 모델별 20회씩을 합한 80회이며, 당시 35건은 현재 경로에 있는 원본 보존 기록으로 남긴다. 이전 60회 계획은 계획 변경 이력으로 표시하되 그 계획에서 생성된 현재 경로의 원본은 현재 80회에 포함하며 pilot으로 옮기지 않는다. 이번 문서 유지보수에서는 실제 모델·Cloud 생성과 후보 Judge를 실행하지 않았으며, 평가 보고서가 생성된 것으로 표시하지 않는다.

## Reasoning 진단의 이동과 집계 예외

당시 구형 경로인 `benchmark/round_1/tomahawk/qwen36/`에서 확인한 run `20260916_124351_312419`는 reasoning 종료 메시지 추가 후 진단이다. `experiment.type=benchmark`로 저장돼 있어도 **현재 본 실험·품질·성능 집계에서 제외한다**. 결과는 `stop`·completion 3703·코드 생성·`RE`이며 [진단 기록](../docs/history/reasoning-budget-diagnostic.md)에 근거를 남겼다.

문서 검증 중 `pilot/reasoning_block/tomahawk/qwen36/`로 이동된 것을 확인했다. 실행기는 같은 경로의 완료 결과를 건너뛰므로 이 진단을 원래 benchmark 경로에 다시 두면 정식 요청이 건너뛰어진다. 경로 분리는 확인했으며 새 결과에는 종료 메시지 설정 기록도 추가했다. 이번 문서 작업에서는 이동·삭제·JSON 수정을 하지 않았다. 이 예외는 run ID로 식별하며 동일 문제의 다른 실행으로 확대하지 않는다.

## 기록과 집계 원칙

본 평가 결과는 `benchmark/<문제>/<모델>/round_<라운드>/`에 저장한다. 폴더는 실제 실행 시 생성한다. 현재 본 실험 요청 설정은 출력 61440·reasoning 53248·temperature 0이며 서버 셸 Context는 65536이다. 기존 종료 메시지는 유지하고 이전 조건의 결과와 구분한다. 새 로컬 benchmark JSON에는 [종료 메시지](../docs/history/reasoning-budget-diagnostic.md)도 generation_config에 기록한다. 실제 서버 적용과 관측값은 파일 설정과 구분해야 한다.

`response.json`은 원본 응답, `candidate.py`는 추출 코드, `result.json`은 설정·응답·생성 지표와 생성 기록 완료 여부다. 새 기록은 `judge=null`이며, 구형 기록의 embedded `judge`는 당시 판정으로 보존한다. 코드가 없으면 `candidate.py`가 없을 수 있다. 초기 보관 기록은 파일명과 스키마가 다를 수 있다.

Pilot의 Qwen Pet은 `length`, completion 6144, `NO_CODE`로 종료했다. 이 실패 기록은 출력 한도를 늘린 근거이며 새 benchmark에 합산하거나 Round 2 입력으로 재사용하지 않는다.

Calibration의 `PASS`는 최종 응답과 코드 블록 생성 여부를 확인한 상태로, 테스트 정답 판정인 `AC`와 다르다. 스트레스 실행기는 당시 비교를 위해 출력 6144·reasoning 2048 설정을 유지한다.

Diagnostics의 수정 코드는 모델 원본 답변이 아니므로 모델 정답률에 포함하지 않는다. 저장된 판정 근거가 없으면 코드 파일만으로 수동 재채점 성공을 단정하지 않는다.

원본 내용은 수정하지 않고 이전 경로와 복원 방법은 [정리 이력](../docs/history/README.md)에 남겼다. 제한 미제공 조건의 이전 Cloud 10회는 pilot으로 보존하고, [Cloud 안내](../docs/operations/cloud-runbook.md)에 따라 현재 계획인 전체 10문항×2회 독립 실행 결과를 Cloud 모델별로 `benchmark/<문제>/luna/round_1/`·`round_2/`와 `benchmark/<문제>/motif3/round_1/`·`round_2/`에 저장한다. Cloud 모델당 20회는 로컬의 40회에 합산하지 않고 두 Cloud 모델끼리도 합산하지 않으며, 최종 로컬 후보 선정에서도 제외한다. 전체 계획은 로컬 40회와 Cloud 40회의 80회이고, 이전 60회 계획은 계획 변경 이력으로 보존하되 그 계획에서 생성된 현재 경로의 원본은 현재 80회에 포함한다. Motif-3는 Luna 실행기를 확장해 추가한 두 번째 Cloud 대상이다. 이번 문서 유지보수에서는 실제 결과 내용과 완료 범위를 재검증하지 않았다. 원본 응답·선택적 후보 코드·정리된 결과를 나누고, 성공·실패 시도를 덮어쓰지 않는다.

모델당 서버 시작 후 warmup 1회를 수행한다.
warmup은 본 실험 40회 및 품질·성능 평균에서 제외한다.
benchmark 문제는 warmup에 사용하지 않는다.

## 워밍업과 본 실험 기록

워밍업은 짧은 요청만 실행하고 결과 파일을 만들지 않는다. environment 인자·환경 JSON 자동 생성·세션 연결·서버 시작 계측도 사용하지 않는다. 기존에 보관한 기록은 삭제하거나 다시 쓰지 않는다.

본 실험 성공·실패 기록과 tok/s·VRAM 수집은 유지한다. VRAM은 현재 서버 PID를 자동 탐색해 관측하며 프로세스 값과 전체 GPU 값을 구분한다. PID 미식별·WSL 미지원·생성 통계 누락은 null과 사유로 남긴다. 새 기록에는 environment 참조가 없다.

## 실행 제한 추가 전 원본 보존

`pilot/pre_resource_limits_20260916_162603_416706/benchmark/round_1/`에 로컬 6건, 같은 보관 폴더의 `cloud/`에 Cloud 10건을 옮겼다. 각각 18·30파일이며 이동 전후 상대 경로별 SHA-256과 바이트 크기를 대조했다. 원래 경로와 해시는 보관 폴더의 `manifest.json`에 남겼다. 기존 `pilot/benchmark_archived/`와 다른 pilot은 수정하지 않았다. 이 파일들은 로컬 보존 자료이며 이번 코드 커밋에는 포함하지 않는다.

새 프롬프트에는 시간·메모리 제한이 포함된다. 메모리 측정·강제·MLE 판정은 없으므로 AC가 메모리 준수를 증명하지 않는다.

## 일괄 채점 세션

`results/judging/<세션 ID>/manifest.json`에 선택 범위, 시작/종료 시각, 처리 상태, 미생성 목록, 원본 run ID·경로·SHA-256, 후보 SHA-256, 시간 제한, 테스트 입출력 파일별 SHA-256, Python·플랫폼·Judge 소스 식별값을 저장한다. 각 `judge.json`에는 기존 Judge 반환값과 원본 연결 정보를 저장한다.

- `complete=true`는 발견한 저장 완료 기록의 처리를 마쳤다는 뜻이다. 전체 계획 80회 생성·품질 평가 완료를 뜻하지 않는다.
- 선택 범위에 미생성 항목이 있으면 `coverage_complete=false`, `status=completed_with_missing`이며 `missing` 목록을 확인한다. 누락이 없으면 `status=completed`다.
- 호출 실패는 `CALL_ERROR`로 채점 제외하며 성공 응답의 코드 미추출은 별도 `NO_CODE` 결과로 남긴다. 호출 실패를 정답률 분모에서 임의로 제외하지 않는다.
- 현재 본 실험 경로만 조회하며 pilot·archive는 제외한다. 기존 embedded Judge 결과가 있어도 새 세션에서 다시 채점한다.
- 수정된 후보나 불완전한 생성 기록은 자동 복구·재호출하지 않는다. 생성 기록의 시간 제한과 현재 문제 목록이 다르면 중단한다.
- Ctrl+C나 채점 오류 시 완료된 개별 파일을 보존하고 세션은 `complete=false`로 남긴다. 강제 종료 시에도 마지막 저장된 미완료 manifest와 개별 결과를 보존한다. 재실행은 새 세션에서 시작한다.
- 동일 저장소의 동시 일괄 채점은 파일 잠금으로 막는다. 채점 중 새 생성 작업을 시작하지 않는다.
- 후속 비교는 사용할 세션 ID를 명시적으로 선택하고 그 세션의 판정을 사용한다. 생성 지표는 해당 `source_run_id`의 원본과 연결한다. 기존 embedded 판정과 새 판정을 섞거나 가장 좋은 회차만 고르지 않는다.

이번 구조 변경은 생성·채점 부하를 분리하기 위한 것이다. 기존 TLE가 추론 부하 때문에 발생했다는 인과는 확인하지 않았으며, 서버 종료 후 실제 일괄 채점과 비교는 별도로 수행한다.

## 평가 결과

기준 `judge batch` 세션은 생성 원본을 공식 1배 시간 제한으로 채점한 결과로 `results/judging/<세션 ID>/`에 남긴다. 평가 후처리는 별도 `results/evaluation/<평가 ID>/`에 저장하며 benchmark·기준 세션·원본 candidate를 덮어쓰지 않는다.

```text
results/evaluation/<평가 ID>/
├── manifest.json
├── policy.json
├── reviews/<문제>/<모델>/round_<회차>/review.json
├── attempts/<문제>/<모델>/round_<회차>/<attempt-id>/
│   ├── attempt.json, attempt.seal
│   ├── candidate.py
│   └── candidate.diff
└── reports/<unique>/
    ├── report.json
    ├── report.md
    └── review-snapshot.json
```

열 문항 모두 공식 1배 제한의 원본 평가와 최소 수정 보조 대상이다. 기준 세션의 개별 테스트에 `TLE`가 있을 때만 해당 문항 전체를 평가 단계 유효 2배 제한으로 다시 실행한다. 기준 세션이 `AC`인 항목은 `baseline_1x`로 재사용하며 2배 측정으로 표시하지 않는다. 네 scoring 문제의 2배 결과는 scoring에 반영하고 여섯 diagnostic 문제의 2배 결과는 진단으로만 남긴다. 여섯 문제의 1배 원본 판정과 보조 수정 결과는 평가에 포함한다. 평가 결과의 `source`는 `baseline_1x`, `limit_2x`, `pending_limits` 중 하나로 구분한다. `pending_limits`와 기타 누락·미확인 항목은 0점이나 실패로 바꾸지 않는다.

`review.json`의 설명 점수는 사람이 직접 입력하며 `NO_CODE`인 정상 응답도 포함한다. `CALL_ERROR`는 설명 점수에서 제외한다. `repair.decision`은 `null`, `not_applicable`, `not_repairable`, `candidate` 중 하나이며, `candidate`에는 사유·알고리즘 보존 여부·저장소 루트 상대 `code_path`를 남긴다. 보조 수정은 원본 candidate를 바꾸지 않고 시도별 `candidate.py`·`candidate.diff`·봉인 파일을 `attempts/` 아래에 저장하며, 같은 원본에 대해 최대 한 번의 보조 통과만 집계한다. 별도의 `judge candidate` 실행은 평가 보고서에 자동 편입하지 않는다. 보고서 파일은 측정값·리뷰 snapshot을 남기지만 최종 실험 보고서의 문장이나 답안을 대신 작성하지 않는다.

성공 호출의 `response_elapsed_seconds` 평균은 코드 유무와 무관하게 성공 호출 n으로 계산한다. 호출 실패 시간과 n은 별도로 표시한다. 평가 기준은 생성 시작 뒤 확정됐으며 `policy.json`에 그 시점을 남긴다. 생성 전체 80회와 실제 후보 채점이 확인되기 전에는 평가 완료로 표시하지 않는다.

## 2026-09-16 생성·채점 분리 후 보관 이력

현재 benchmark의 Qwen 9건·Luna 10건을 `results/pilot/pre_offline_judging_20260916_173157_900249/benchmark/`로 옮겼다. 원본 54파일(3,421,076바이트)의 이동 전후 경로별 SHA-256·크기를 대조했고 결과를 같은 보관 폴더의 `manifest.json`에 남겼다. 기존 응답·코드·판정·호출 실패는 수정하지 않았다. 이 기록은 새 본 실험 및 일괄 채점 대상에서 제외한다.

이동 당시 생성기·채점기는 실행 중이지 않았으며 모델 서버는 종료하지 않았다. 보관 작업 직후의 `results/benchmark/`는 빈 상태였다. 이후 생성 중인 현재 상태와 구분하며 최신 진행은 [결정 이력](../docs/history/decision-log.md)를 따른다. 새 실행이나 실제 채점은 이 보관 작업에서 수행하지 않았다.

## 생성 코드와 판정 읽기

추출기는 마지막 Python 코드 블록을 선택하고, Python 블록이 없으면 마지막 일반 코드 블록을 사용합니다. 코드 블록이 없으면 생성 기록의 `extracted_code`는 null이며, 후속 일괄 채점에서 `NO_CODE`로 기록합니다.

Judge는 `<문제 이름>.in.*`와 대응하는 `.out.*` 파일을 사용하며, `.dummy.in.*` 예제 파일은 채점 대상에서 제외됩니다. 각 테스트를 별도 Python 프로세스로 실행하고 문제의 시간 제한을 적용합니다. 출력은 공백으로 나눈 토큰 단위로 비교합니다.

| 판정 | 의미 |
| --- | --- |
| `AC` | 모든 테스트 통과 |
| `WA` | 출력 불일치 |
| `TLE` | 테스트 실행 시간 초과 |
| `RE` | 실행 중 오류로 비정상 종료 |
| `NO_CODE` | 추출할 코드 블록 없음 |
| `OLE` | 테스트별 stdout·stderr 합산 출력이 10 MiB(10,485,760 bytes)를 초과함 |
| `JUDGE_ERROR` | 채점 인프라·처리 예외로 해당 항목의 판정을 완료하지 못함; 후보 코드 판정과 구분함 |

선택한 채점 세션의 `judge.json`에서 통과 수·전체 테스트 수·테스트별 판정·최대 실행 시간을 확인할 수 있습니다. Judge는 테스트별 시간 제한과 stdout·stderr 합산 10 MiB 출력 한도를 적용하고, 시간 초과와 출력 초과가 함께 발생하면 먼저 발생한 자원을 `TLE` 또는 `OLE`로 기록합니다. 이 정책의 `version`, `per_test_output_limit_bytes`, `output_limit_scope`, `resource_verdict_precedence`는 세션 `manifest.json`의 `judge_policy`에 남깁니다. 인프라·처리 예외는 `JUDGE_ERROR`로 남기며 정상 판정과 섞지 않습니다. 기존 생성 기록에 포함된 `judge`는 당시 판정으로 보존하며 새 채점과 섞지 않습니다. 모델의 응답 생성 시간과 생성된 코드의 테스트 실행 시간은 별도 지표입니다. 풀이 설명의 정확성은 응답 원문을 읽고 평가합니다.

공식 메모리 제한은 모델 입력에 제공하지만, Judge는 코드의 메모리 사용량·RSS를 측정하거나 메모리 제한을 강제하지 않습니다. AC는 메모리 제한 준수를 증명하지 않습니다. 현재 Judge는 샌드박스를 구현하지 않았으며, 생성 코드를 로컬 권한으로 실행합니다. 결과는 이 실행 환경의 관측값이며 대회 공식 채점 결과와 같음을 보장하지 않습니다.

실행·재개·채점 명령은 [로컬 실행 안내](../docs/operations/local-runbook.md), 측정 의미와 기록 한계는 [기록 구현 점검](../docs/operations/recording.md)을 따른다.
