# 실행 결과

| 경로 | 용도 | 본 실험 집계 |
| --- | --- | --- |
| `benchmark/` | 고정 설정으로 수행하는 본 평가 | 아래 진단 예외를 제외하고 포함 |
| `pilot/reasoning_block/` | Reasoning 종료 메시지 추가 후 Tomahawk 진단 | 제외 |
| [pilot/6144](pilot/6144/) | 출력 한도 6144에서 중단한 초기 benchmark 8회 | 제외 |
| [calibration/stress](calibration/stress/) | 생성 한도 결정용 스트레스 실행 | 제외 |
| [diagnostics/struktura](diagnostics/struktura/) | WA 원인을 확인하기 위한 수동 코드 수정본 | 제외 |
| [archive/legacy-runs](archive/legacy-runs/) | 초기 연결·Ollama 실습·benchmark 개발 과정의 timestamp 결과 | 제외 |

## Reasoning 진단의 이동과 집계 예외

처음 `benchmark/round_1/tomahawk/qwen36/`에서 확인한 run `20260916_124351_312419`는 reasoning 종료 메시지 추가 후 진단이다. `experiment.type=benchmark`로 저장돼 있어도 **본 실험 40회·품질·성능 집계에서 제외한다**. 결과는 `stop`·completion 3703·코드 생성·`RE`이며 [진단 기록](../docs/reasoning-budget-diagnostic.md)에 근거를 남겼다.

문서 검증 중 `pilot/reasoning_block/tomahawk/qwen36/`로 이동된 것을 확인했다. 실행기는 같은 경로의 완료 결과를 건너뛰므로 이 진단을 원래 benchmark 경로에 다시 두면 정식 요청이 건너뛰어진다. 경로 분리는 확인했으며 요청 설정 기록 보완은 남아 있다. 이번 문서 작업에서는 이동·삭제·JSON 수정을 하지 않았다. 이 예외는 run ID로 식별하며 동일 문제의 다른 실행으로 확대하지 않는다.

## 기록과 집계 원칙

본 평가 결과는 `benchmark/round_<라운드>/<문제>/<모델>/`에 저장한다. 폴더는 실제 실행 시 생성한다. 현재 로컬 요청 설정은 출력 8192·reasoning 2048·temperature 0이며 서버 셸 Context는 12288이다. 현재 작업 트리의 공통 요청에는 [종료 메시지](../docs/reasoning-budget-diagnostic.md)도 있지만 benchmark JSON에 해당 설정은 아직 기록되지 않는다. 실제 서버 적용과 관측값은 파일 설정과 구분해야 한다.

`response.json`은 원본 응답, `candidate.py`는 추출 코드, `result.json`은 설정·응답·판정 기록이다. 코드가 없으면 `candidate.py`가 없을 수 있다. 초기 보관 기록은 파일명과 스키마가 다를 수 있다.

Pilot의 Qwen Pet은 `length`, completion 6144, `NO_CODE`로 종료했다. 이 실패 기록은 출력 한도를 늘린 근거이며 새 benchmark에 합산하거나 Round 2 입력으로 재사용하지 않는다.

Calibration의 `PASS`는 최종 응답과 코드 블록 생성 여부를 확인한 상태로, 테스트 정답 판정인 `AC`와 다르다. 스트레스 실행기는 당시 비교를 위해 출력 6144·reasoning 2048 설정을 유지한다.

Diagnostics의 수정 코드는 모델 원본 답변이 아니므로 모델 정답률에 포함하지 않는다. 저장된 판정 근거가 없으면 코드 파일만으로 수동 재채점 성공을 단정하지 않는다.

원본 내용은 수정하지 않고 이전 경로와 복원 방법은 [정리 이력](../docs/history/README.md)에 남겼다. Cloud 비교 결과는 아직 없으며, 공통 5문항 각 1회라는 별도 조건에 맞춰 이후 저장 방식을 정한다.

모델당 서버 시작 후 warmup 1회를 수행한다.
warmup은 본 실험 40회 및 품질·성능 평균에서 제외한다.
benchmark 문제는 warmup에 사용하지 않는다.

## 워밍업과 본 실험 기록

워밍업은 짧은 요청만 실행하고 결과 파일을 만들지 않는다. environment 인자·환경 JSON 자동 생성·세션 연결·서버 시작 계측도 사용하지 않는다. 기존에 보관한 기록은 삭제하거나 다시 쓰지 않는다.

본 실험 성공·실패 기록과 tok/s·VRAM 수집은 유지한다. VRAM은 현재 서버 PID를 자동 탐색해 관측하며 프로세스 값과 전체 GPU 값을 구분한다. PID 미식별·WSL 미지원·생성 통계 누락은 null과 사유로 남긴다. 새 기록에는 environment 참조가 없다.
