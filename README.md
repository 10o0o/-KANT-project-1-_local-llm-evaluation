# 로컬 LLM 코딩테스트 평가

Qwen과 Gemma가 생성한 Python 풀이를 공개 테스트 데이터로 실행·채점하고 결과를 비교하는 프로젝트입니다. 정답 여부와 함께 풀이 설명, 추론 내용, 생성 속도를 살펴보며 코딩테스트 풀이에 적합한 로컬 모델을 찾습니다.

COCI에서 선정한 10문항을 사용합니다. 현재 실행기는 모델 하나에 문제 하나를 요청하고, 응답 저장부터 코드 추출·채점까지 이어서 처리합니다. 전체 문항의 반복 실험과 최종 비교는 진행 중입니다.

```text
문제문 → llama.cpp 모델 호출 → 응답 저장 → Python 코드 추출 → 로컬 Judge → 결과 저장
```

## 실행 환경

- Python 3.12, uv
- `--reasoning-budget`을 지원하는 llama.cpp 빌드와 `llama-server`
- 해당 llama.cpp에서 로딩할 수 있는 Qwen·Gemma GGUF 가중치
- COCI 문제별 테스트 입력·정답 파일

확인한 장비·버전·모델 파일과 실제 관측 범위는 [실행 환경과 측정 근거](docs/environment.md)에 정리했습니다. 서버 스크립트의 GPU 설정은 이 환경에서 사용한 값이므로 장비에 맞게 조정해야 합니다. 모델 가중치, llama.cpp 런타임, 테스트 데이터는 저장소에 포함하지 않습니다.

## 설치와 실행

### 1. Python 환경 준비

저장소를 내려받은 뒤 루트에서 실행합니다.

```bash
git clone https://github.com/10o0o/-KANT-project-1-_local-llm-evaluation.git
cd -- -KANT-project-1-_local-llm-evaluation
uv sync --locked
```

의존성과 패키지 설정은 [pyproject.toml](pyproject.toml), 고정된 버전은 [uv.lock](uv.lock)에 있습니다.

### 2. 테스트 데이터 준비

[COCI 공식 자료](https://hsin.hr/coci/)의 2025/2026 시즌 Contest 4·5·6에서 Test data를 내려받고, [problems.json](data/coci/problems.json)의 `problem_dir`에 맞춰 문제별 파일을 배치합니다. 예를 들어 Skare의 경로는 다음과 같습니다.

```text
data/coci/2025_2026/contest5/testdata/skare/
├── skare.in.1a
├── skare.out.1a
└── ...
```

선정 문항의 영어 문제문은 같은 JSON의 `statement_path`에 있습니다. 모델에는 설명·입출력 조건·제약·예제를 전달하고, 제목·대회 정보·시간 제한·난이도 등 평가용 메타데이터는 분리합니다. 원본 PDF와 테스트 데이터의 출처는 COCI이며, 이 저장소가 해당 자료에 별도의 라이선스를 부여하지 않습니다.

문제문에 포함된 그림은 Markdown에서 확인할 수 있습니다. 현재 호출기는 텍스트만 전송하므로 이미지 파일 자체는 모델에 전달되지 않습니다.

### 3. 서버 실행

별도 터미널에서 사용할 모델 하나를 시작한다. 기본 경로가 설치 위치와 다르면 `LLAMA_ROOT`, `GEMMA4_MODEL_PATH` 또는 `QWEN36_MODEL_PATH`를 지정한다.

```bash
bash configs/llama.cpp/gemma4.sh
# Qwen을 실행할 때:
# bash configs/llama.cpp/qwen36.sh
```

서버 터미널에서 준비 완료를 확인한 뒤 워밍업을 실행한다. 두 서버는 `127.0.0.1:8080`을 공유하므로 모델 전환 시 기존 서버를 종료한다. 환경 JSON이나 별도 시작 실행기는 사용하지 않는다.

| 서버 설정 | Qwen | Gemma |
| --- | --- | --- |
| API 모델 이름 | `qwen36` | `gemma4` |
| Context | 12288 | 12288 |
| 기본 출력 / reasoning / temperature | 8192 / 2048 / 0 | 8192 / 2048 / 0 |
| Parallel / Flash Attention | 1 / on | 1 / on |
| GPU layers | all | auto |
| CPU MoE layers | 32 | 미지정 |
| Generation / batch threads | 16 / 24 | 미지정 |
| Load mode | none | 미지정 |
| RAM prompt cache | 0 MiB (비활성) | 0 MiB (비활성) |

미지정 옵션은 런타임 기본값을 따른다. `--fit` 동작은 변경하지 않았다. 표는 설정값이며 실제 적재 상태·VRAM 적합성은 직접 실행해서 확인한다.

### 4. 워밍업 후 두 회차 평가

다른 터미널에서 실행한다. 아래는 Qwen 예시이며 Gemma는 `--model gemma4`로 바꾼다.

```bash
uv run python scripts/run_warmup.py --model qwen36

uv run python scripts/run_benchmark.py \
  --model qwen36 --problems all --round 1

uv run python scripts/run_benchmark.py \
  --model qwen36 --problems all --round 2
```

워밍업은 모델당 별도 짧은 입력으로 호출하고 완료 여부만 터미널에 표시한다. 파일 저장·환경 기록·성능 측정은 하지 않는다. 실패하면 오류를 그대로 전달한다. 워밍업은 본 실험 40회와 평균에서 제외한다. 요청은 출력 128·reasoning 64·temperature 0이다.

`--problems`에는 `all` 또는 `problems.json`의 ID를 쉼표로 나열한다. 본 실험은 동일 문제문·지시문·생성 설정으로 두 번 독립 요청한다. 이전 답변이나 채점 결과는 전달하지 않으며 Round 1 없이 Round 2도 실행할 수 있다. 공통 요청의 `cache_prompt=false`와 서버의 `--cache-ram 0`은 유지한다. 여기서 독립 요청은 이전 답변을 전달하지 않는 절차를 뜻한다. 응답의 캐시 카운터는 해당 요청의 근거이며 전체 실험의 독립성을 단독으로 증명하지 않는다.

설정 변경은 서버 재시작이 필요하다. 실행할 모델과 서버를 직접 맞춘다. 환경 파일 연결·검증은 하지 않는다. 클라이언트 timeout은 3600초이며 자동 재시도는 꺼져 있다. 호출 실패는 기록한 뒤 중단하고, 같은 명령 재실행 시 보존된 실패 시도는 건너뛴다.

과거 calibration·diagnostic 실행기는 당시 실험용이다. 과거 Ollama 실습은 [정리 전 Git 이력](docs/history/README.md)에 보존했다.

## 결과 확인

실행 결과는 다음 위치에 저장합니다.

```text
results/benchmark/round_<라운드>/<문제 이름>/<모델 이름>/
├── response.json   # API 원본 응답
├── candidate.py    # 추출한 Python 코드가 있을 때 생성
└── result.json     # 생성 설정·응답·추론·사용량·채점 결과
```

`--problems all`은 전체 문제를, 쉼표로 구분한 ID는 지정한 문제들을 순서대로 실행합니다. 같은 라운드·문제·모델의 완료 결과는 건너뜁니다. 불완전한 결과 폴더는 덮어쓰지 않고 중단합니다.

기존 출력 한도 6144의 8회 실행은 [pilot/6144](results/pilot/6144/)에 보존했습니다. 당시 Qwen Pet이 6144토큰에서 `length`로 종료하고 `NO_CODE`가 되어 출력 한도를 8192로 늘렸던 이력이 있습니다.

본 실험 설정을 서버 Context 12288, 공통 요청 max_tokens 8192 / reasoning 2048 / temperature 0 / cache_prompt false로 동결했다. Pilot은 본 실험 집계에서 제외하며 두 회차 어느 쪽에서도 이전 답변으로 전달하지 않는다.

본 실험은 요청·응답·실패·전체 응답 시간·토큰·생성 속도·채점 결과를 계속 저장한다. 환경 세션 파일과의 연결 및 서버 시작 계측은 제거했다. 요청별 로딩 시간은 llama.cpp 응답에 없어 null과 사유를 남긴다.

VRAM은 응답 원본 저장 후 또는 호출 실패 직후 조회한다. 현재 8080 포트를 사용하는 llama-server와 모델 별칭으로 PID를 자동 탐색한다. 서버를 하나로 식별하지 못하거나 WSL에서 프로세스 값이 제공되지 않으면 null과 사유를 남긴다. `memory.process`(프로세스)와 `memory.devices`(전체 장치)는 서로 대체하지 않으며 최대 VRAM으로 표시하지 않는다. 전체 응답 시간에는 VRAM 조회·파일 저장·채점 시간이 포함되지 않는다.

모델별 집계에는 호출 성공 수/시도 수와 지표별 평균·n을 표시한다. 누락값을 0으로 대체하지 않는다. 실행 도구·모델 파일·설정의 확인 범위는 [환경 문서](docs/environment.md)에 정리하며 자동 환경 기록이 있는 것으로 간주하지 않는다.

추출기는 마지막 Python 코드 블록을 선택하고, Python 블록이 없으면 마지막 일반 코드 블록을 사용합니다. 코드 블록이 없으면 `NO_CODE`로 기록합니다.

Judge는 `<문제 이름>.in.*`와 대응하는 `.out.*` 파일을 사용하며, `.dummy.in.*` 예제 파일은 채점 대상에서 제외됩니다. 각 테스트를 별도 Python 프로세스로 실행하고 문제의 시간 제한을 적용합니다. 출력은 공백으로 나눈 토큰 단위로 비교합니다.

| 판정 | 의미 |
| --- | --- |
| `AC` | 모든 테스트 통과 |
| `WA` | 출력 불일치 |
| `TLE` | 테스트 실행 시간 초과 |
| `RE` | 실행 중 오류로 비정상 종료 |
| `NO_CODE` | 추출할 코드 블록 없음 |

`result.json`의 `judge`에서 통과 수·전체 테스트 수·테스트별 판정·최대 실행 시간을 확인할 수 있습니다. 실패가 여러 종류면 전체 판정에는 첫 실패의 상태를 기록합니다. 모델의 응답 생성 시간과 생성된 코드의 테스트 실행 시간은 별도 지표입니다. 풀이 설명의 정확성은 응답 원문을 읽고 평가합니다.

현재 Judge는 메모리 제한과 샌드박스를 구현하지 않았으며, 생성 코드를 로컬 권한으로 실행합니다. 결과는 이 실행 환경의 관측값이며 대회 공식 채점 결과와 같음을 보장하지 않습니다.

## 저장소 구성과 문서

```text
configs/llama.cpp/   모델 서버 실행 스크립트
scripts/            benchmark·데이터 검증 진입점과 calibration 실행기
src/llm_eval/benchmark/  CLI·프롬프트·문제별 실행
src/llm_eval/       모델 호출·문제 선택·코드 추출·채점
data/coci/         문제 목록과 모델 입력용 문제문
results/            실행별 응답·후보 코드·채점 결과
docs/               프로젝트 요구사항과 조사·학습 기록
```

| 문서 | 내용 |
| --- | --- |
| [요구사항](docs/requirements.md) | 평가 목적과 모델 선정 기준 |
| [모델 조사](docs/models.md) | 후보 모델 정보와 실행 경과 |
| [실행 환경](docs/environment.md) | 장비·버전·모델 파일과 측정 근거·미확인 항목 |
| [발제 원문](docs/project-brief.md) | 프로젝트 과제 기준 |
| [단계별 안내](docs/guide.md) | 실습 단계와 참고 자료 |
| [진행 기록](STATE.md) | 학습 과정과 확인 근거 |
| [튜터 지침](AGENTS.md) | AI 활용과 작업 범위 |

실행 결과의 용도와 집계 범위는 [결과 분류](results/README.md), 이전 파일의 위치와 복원 방법은 [정리 이력](docs/history/README.md)에 정리했습니다.

현재 benchmark는 llama.cpp 로컬 모델용입니다. 발제 STEP 7의 Cloud 모델 1개·공통 5문항·각 1회 비교는 이후 추가할 단계이며, 이번 구조화에 Cloud 호출 기능은 포함하지 않았습니다. 기존 문제 로딩·프롬프트·코드 추출·Judge를 재사용할 수 있도록 실행 진입점과 역할을 분리했습니다.

llama.cpp 전환은 튜터에게 허락받았다. [평가 기준](docs/requirements.md)과 [기록 복구 점검](docs/logging-review.md)을 따른다. 기록 복구와 본 실험 준비는 아직 완료되지 않았다.

## 모의 검증

```bash
uv run python -m unittest discover -s tests -v
```

모델 응답과 GPU 조회를 모의 처리하고 워밍업 무저장·본 실험 기록 유지를 확인한다. 이 검증은 실제 서버 실행, 모델 품질·VRAM 적합성이나 본 실험 완료를 증명하지 않는다.
