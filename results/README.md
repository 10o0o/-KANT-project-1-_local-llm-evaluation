# 실행 결과

| 경로 | 용도 | 본 실험 집계 |
| --- | --- | --- |
| `benchmark/<문제>/luna/round_1/` | Cloud 10문항×1회, 로컬과 별도 비교 | Cloud 집계 |
| `benchmark/<문제>/<qwen36 또는 gemma4>/round_<회차>/` | 로컬 모델당 10문항×2회 | 로컬 집계 |
| `pilot/pre_resource_limits_20260916_162603_416706/` | 실행 제한 미제공 조건의 로컬 6회·Cloud 10회와 이동 manifest | 제외 |
| `pilot/reasoning_block/` | Reasoning 종료 메시지 추가 후 Tomahawk 진단 | 제외 |
| [pilot/6144](pilot/6144/) | 출력 한도 6144에서 중단한 초기 benchmark 8회 | 제외 |
| [calibration/stress](calibration/stress/) | 생성 한도 결정용 스트레스 실행 | 제외 |
| [diagnostics/struktura](diagnostics/struktura/) | WA 원인을 확인하기 위한 수동 코드 수정본 | 제외 |
| [archive/legacy-runs](archive/legacy-runs/) | 초기 연결·Ollama 실습·benchmark 개발 과정의 timestamp 결과 | 제외 |

## Reasoning 진단의 이동과 집계 예외

처음 `benchmark/round_1/tomahawk/qwen36/`에서 확인한 run `20260916_124351_312419`는 reasoning 종료 메시지 추가 후 진단이다. `experiment.type=benchmark`로 저장돼 있어도 **본 실험 40회·품질·성능 집계에서 제외한다**. 결과는 `stop`·completion 3703·코드 생성·`RE`이며 [진단 기록](../docs/reasoning-budget-diagnostic.md)에 근거를 남겼다.

문서 검증 중 `pilot/reasoning_block/tomahawk/qwen36/`로 이동된 것을 확인했다. 실행기는 같은 경로의 완료 결과를 건너뛰므로 이 진단을 원래 benchmark 경로에 다시 두면 정식 요청이 건너뛰어진다. 경로 분리는 확인했으며 새 결과에는 종료 메시지 설정 기록도 추가했다. 이번 문서 작업에서는 이동·삭제·JSON 수정을 하지 않았다. 이 예외는 run ID로 식별하며 동일 문제의 다른 실행으로 확대하지 않는다.

## 기록과 집계 원칙

본 평가 결과는 `benchmark/<문제>/<모델>/round_<라운드>/`에 저장한다. 폴더는 실제 실행 시 생성한다. 현재 본 실험 요청 설정은 출력 61440·reasoning 53248·temperature 0이며 서버 셸 Context는 65536이다. 기존 종료 메시지는 유지하고 이전 조건의 결과와 구분한다. 새 로컬 benchmark JSON에는 [종료 메시지](../docs/reasoning-budget-diagnostic.md)도 generation_config에 기록한다. 실제 서버 적용과 관측값은 파일 설정과 구분해야 한다.

`response.json`은 원본 응답, `candidate.py`는 추출 코드, `result.json`은 설정·응답·생성 지표와 생성 기록 완료 여부다. 새 기록은 `judge=null`이며, 구형 기록의 embedded `judge`는 당시 판정으로 보존한다. 코드가 없으면 `candidate.py`가 없을 수 있다. 초기 보관 기록은 파일명과 스키마가 다를 수 있다.

Pilot의 Qwen Pet은 `length`, completion 6144, `NO_CODE`로 종료했다. 이 실패 기록은 출력 한도를 늘린 근거이며 새 benchmark에 합산하거나 Round 2 입력으로 재사용하지 않는다.

Calibration의 `PASS`는 최종 응답과 코드 블록 생성 여부를 확인한 상태로, 테스트 정답 판정인 `AC`와 다르다. 스트레스 실행기는 당시 비교를 위해 출력 6144·reasoning 2048 설정을 유지한다.

Diagnostics의 수정 코드는 모델 원본 답변이 아니므로 모델 정답률에 포함하지 않는다. 저장된 판정 근거가 없으면 코드 파일만으로 수동 재채점 성공을 단정하지 않는다.

원본 내용은 수정하지 않고 이전 경로와 복원 방법은 [정리 이력](../docs/history/README.md)에 남겼다. 이전 Cloud 10회는 pilot으로 보존하고, [Cloud 안내](../docs/cloud-benchmark.md)에 따라 전체 10문항×1회 결과를 `benchmark/<문제>/luna/round_1/`에 저장한다. 로컬의 40회에 합산하지 않는다. 원본 응답·선택적 후보 코드·정리된 결과를 나누고, 성공·실패 시도를 덮어쓰지 않는다.

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

- `complete=true`는 발견한 저장 완료 기록의 처리를 마쳤다는 뜻이다. 전체 50회 생성·품질 평가 완료를 뜻하지 않는다.
- 선택 범위에 미생성 항목이 있으면 `coverage_complete=false`, `status=completed_with_missing`이며 `missing` 목록을 확인한다. 누락이 없으면 `status=completed`다.
- 호출 실패는 `CALL_ERROR`로 채점 제외하며 성공 응답의 코드 미추출은 별도 `NO_CODE` 결과로 남긴다. 호출 실패를 정답률 분모에서 임의로 제외하지 않는다.
- 현재 본 실험 경로만 조회하며 pilot·archive는 제외한다. 기존 embedded Judge 결과가 있어도 새 세션에서 다시 채점한다.
- 수정된 후보나 불완전한 생성 기록은 자동 복구·재호출하지 않는다. 생성 기록의 시간 제한과 현재 문제 목록이 다르면 중단한다.
- Ctrl+C나 채점 오류 시 완료된 개별 파일을 보존하고 세션은 `complete=false`로 남긴다. 강제 종료 시에도 마지막 저장된 미완료 manifest와 개별 결과를 보존한다. 재실행은 새 세션에서 시작한다.
- 동일 저장소의 동시 일괄 채점은 파일 잠금으로 막는다. 채점 중 새 생성 작업을 시작하지 않는다.
- 후속 비교는 사용할 세션 ID를 명시적으로 선택하고 그 세션의 판정을 사용한다. 생성 지표는 해당 `source_run_id`의 원본과 연결한다. 기존 embedded 판정과 새 판정을 섞거나 가장 좋은 회차만 고르지 않는다.

이번 구조 변경은 생성·채점 부하를 분리하기 위한 것이다. 기존 TLE가 추론 부하 때문에 발생했다는 인과는 확인하지 않았으며, 서버 종료 후 실제 일괄 채점과 비교는 별도로 수행한다.
