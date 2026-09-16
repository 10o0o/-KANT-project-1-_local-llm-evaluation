# 실행 결과

| 경로 | 용도 | 본 실험 집계 |
| --- | --- | --- |
| `environment/` | 서버 세션별 설정·관측·파일 식별값·원본 로그·종료 기록 | 시작 시간은 세션별 별도 해석 |
| `benchmark/` | 고정 설정으로 수행하는 본 평가 | 포함 |
| [pilot/6144](pilot/6144/) | 출력 한도 6144에서 중단한 초기 benchmark 8회 | 제외 |
| [calibration/stress](calibration/stress/) | 생성 한도 결정용 스트레스 실행 | 제외 |
| [diagnostics/struktura](diagnostics/struktura/) | WA 원인을 확인하기 위한 수동 코드 수정본 | 제외 |
| [archive/legacy-runs](archive/legacy-runs/) | 초기 연결·Ollama 실습·benchmark 개발 과정의 timestamp 결과 | 제외 |
| `warmup/` | 모델별 API 경로 워밍업 1회 | 제외 |

본 평가 결과는 `benchmark/round_<라운드>/<문제>/<모델>/`에 저장한다. 폴더는 실제 실행 시 생성한다. 현재 로컬 요청 설정은 출력 8192·reasoning 2048·temperature 0이며 서버 셸 Context는 12288이다. 실제 서버 적용과 관측값은 파일 설정과 구분해야 한다.

`response.json`은 원본 응답, `candidate.py`는 추출 코드, `result.json`은 설정·응답·판정 기록이다. 코드가 없으면 `candidate.py`가 없을 수 있다. 초기 보관 기록은 파일명과 스키마가 다를 수 있다.

Pilot의 Qwen Pet은 `length`, completion 6144, `NO_CODE`로 종료했다. 이 실패 기록은 출력 한도를 늘린 근거이며 새 benchmark에 합산하거나 Round 2 입력으로 재사용하지 않는다.

Calibration의 `PASS`는 최종 응답과 코드 블록 생성 여부를 확인한 상태로, 테스트 정답 판정인 `AC`와 다르다. 스트레스 실행기는 당시 비교를 위해 출력 6144·reasoning 2048 설정을 유지한다.

Diagnostics의 수정 코드는 모델 원본 답변이 아니므로 모델 정답률에 포함하지 않는다. 저장된 판정 근거가 없으면 코드 파일만으로 수동 재채점 성공을 단정하지 않는다.

원본 내용은 수정하지 않고 이전 경로와 복원 방법은 [정리 이력](../docs/history/README.md)에 남겼다. Cloud 비교 결과는 아직 없으며, 공통 5문항 각 1회라는 별도 조건에 맞춰 이후 저장 방식을 정한다.

모델당 서버 시작 후 warmup 1회를 수행한다.
warmup은 본 실험 40회 및 품질·성능 평균에서 제외한다.
benchmark 문제는 warmup에 사용하지 않는다.

## 환경과 관측 연결

`start_model.py`가 세션별 `environment.json`, `server.log`, `exit.json`을 만든다. `--environment`로 해당 JSON을 워밍업·본 실험에 전달한다. 성공·호출 실패 레코드 모두 세션 ID·환경 경로·SHA-256을 보존한다. 환경 오류로 요청 전에 중단한 경우는 모델 호출 시도가 아니다.

서버 시작 시간은 준비 완료까지의 시간이며 순수 모델 로딩이나 요청 시간이 아니다. 요청별 로딩 시간은 null과 미제공 사유를 기록한다. 환경 파일은 준비 완료 후 변경하지 않으며 종료 정보는 별도 파일에 남긴다. 시작 실패 기록도 삭제·덮어쓰지 않는다.

VRAM은 `memory.process`(서버 프로세스)와 `memory.devices`(전체 장치)를 구분한 시점 관측값이다. WSL에서 프로세스 값을 못 얻으면 null과 사유를 남긴다. 프로세스 값 대신 장치 값을 쓰거나 최대 VRAM으로 표기하지 않는다. 생성 통계 누락도 null과 사유로 보존한다.

워밍업 결과 폴더가 존재하면 재실행은 중단한다. 실패나 서버 재시작으로 추가 워밍업이 필요하면 원본을 별도 보관하고 추가 실행 경과를 기록한다. 이 문서는 구현 상태이며 실제 환경 관측·워밍업 성공 근거가 아니다.
