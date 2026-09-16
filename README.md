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

개발 환경은 WSL2와 NVIDIA GeForce RTX 5060 Laptop GPU(8 GB VRAM)입니다. 서버 스크립트의 GPU 설정은 이 환경에서 사용한 값이므로 장비에 맞게 조정해야 합니다. 모델 가중치, llama.cpp 런타임, 테스트 데이터는 저장소에 포함하지 않습니다.

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

### 3. 모델 서버 실행

별도 터미널에서 사용할 모델의 서버 하나를 실행합니다. 아래 경로는 설치 위치에 맞게 바꿉니다.

Gemma:

```bash
LLAMA_ROOT=/path/to/llama.cpp \
GEMMA4_MODEL_PATH=/path/to/gemma4/model.gguf \
bash configs/llama.cpp/gemma4.sh
```

Qwen:

```bash
LLAMA_ROOT=/path/to/llama.cpp \
QWEN36_MODEL_PATH=/path/to/qwen36/model.gguf \
bash configs/llama.cpp/qwen36.sh
```

두 서버는 모두 `127.0.0.1:8080`을 사용합니다. 모델을 바꿀 때는 실행 중인 서버를 종료한 뒤 다른 서버를 시작합니다. 서버의 모델 로딩이 끝난 후 문제 실행기를 호출합니다.

| 항목 | Gemma | Qwen |
| --- | --- | --- |
| API 모델 이름 | `gemma4` | `qwen36` |
| Context | 12288 | 12288 |
| GPU 설정 | `--gpu-layers auto` | `--gpu-layers all --n-cpu-moe 28` |
| 서버 기본 출력 한도 | 8192 | 8192 |
| 서버 기본 reasoning budget | 2048 | 2048 |
| Temperature | 0 | 0 |

서버 설정은 [configs/llama.cpp](configs/llama.cpp/)에 있습니다. Python 요청의 출력·추론 한도는 아래 실행기에서 별도로 지정합니다.

### 4. 문제 선택과 평가

[scripts/run_benchmark.py](scripts/run_benchmark.py)에 모델·문제 ID·라운드를 전달합니다.

```bash
uv run python scripts/run_benchmark.py \
  --model qwen36 --problems coci_2025_2026_c5_skare --round 1
```

`--model`은 `qwen36` 또는 `gemma4`, `--problems`은 `problems.json`에 등록한 ID를 사용합니다. Round 1과 Round 2는 같은 문제문·지시문·생성 설정의 독립 반복입니다. 각 요청은 새 대화이며 이전 답변과 채점 결과를 전달하지 않습니다. Round 1 결과가 없어도 Round 2를 실행할 수 있습니다.

```bash
uv run python scripts/run_benchmark.py \
  --model qwen36 --problems coci_2025_2026_c5_skare --round 2
```

현재 요청 설정은 [benchmark/runner.py](src/llm_eval/benchmark/runner.py), 서버 기본값은 [configs/llama.cpp](configs/llama.cpp/)에서 확인합니다. 현재 튜닝 중이며 본 실험 전에 최종 조건을 고정하고 실제 적용값을 확인합니다. 변경한 서버 설정은 **서버를 재시작해야** 적용됩니다. VRAM 적합성과 문제 입력의 수용 여부는 실제 실행으로 확인해야 합니다.

실행기는 `http://127.0.0.1:8080/v1`에 연결합니다. 클라이언트 timeout은 3600초이며 자동 재시도는 꺼져 있습니다. 연결 오류는 서버 터미널을, 테스트 케이스를 찾을 수 없다는 오류는 `problem_dir`와 압축 해제 위치를 확인합니다.

과거 Ollama 실습과 HyperCLOVA 진단 코드는 [정리 전 Git 이력](docs/history/README.md)에서 확인할 수 있습니다.

## 결과 확인

실행 결과는 다음 위치에 저장합니다.

```text
results/benchmark/round_<라운드>/<문제 이름>/<모델 이름>/
├── response.json   # API 원본 응답
├── candidate.py    # 추출한 Python 코드가 있을 때 생성
└── result.json     # 생성 설정·응답·추론·사용량·채점 결과
```

`--problems all`은 전체 문제를, 쉼표로 구분한 ID는 지정한 문제들을 순서대로 실행합니다. 같은 라운드·문제·모델의 완료 결과는 건너뜁니다. 불완전한 결과 폴더는 덮어쓰지 않고 중단합니다.

기존 출력 한도 6144의 8회 실행은 [pilot/6144](results/pilot/6144/)에 보존했습니다. 당시 Qwen Pet이 6144토큰에서 `length`로 종료하고 `NO_CODE`가 되어 출력 한도를 8192로 늘렸던 이력이 있습니다. reasoning 부족으로 단정한 것은 아닙니다. 현재 요청 출력 한도는 튜닝 과정에서 6144이며 최종 설정은 미확정입니다. 최종 조건을 고정한 뒤 본 실험 40회는 처음부터 진행합니다. Pilot은 본 실험 집계에서 제외하며 두 회차 어느 쪽에서도 이전 답변으로 전달하지 않습니다.

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
| [발제 원문](docs/project-brief.md) | 프로젝트 과제 기준 |
| [단계별 안내](docs/guide.md) | 실습 단계와 참고 자료 |
| [진행 기록](STATE.md) | 학습 과정과 확인 근거 |
| [튜터 지침](AGENTS.md) | AI 활용과 작업 범위 |

실행 결과의 용도와 집계 범위는 [결과 분류](results/README.md), 이전 파일의 위치와 복원 방법은 [정리 이력](docs/history/README.md)에 정리했습니다.

현재 benchmark는 llama.cpp 로컬 모델용입니다. 발제 STEP 7의 Cloud 모델 1개·공통 5문항·각 1회 비교는 이후 추가할 단계이며, 이번 구조화에 Cloud 호출 기능은 포함하지 않았습니다. 기존 문제 로딩·프롬프트·코드 추출·Judge를 재사용할 수 있도록 실행 진입점과 역할을 분리했습니다.

llama.cpp 전환은 튜터에게 허락받았다. [평가 기준](docs/requirements.md)과 [기록 복구 점검](docs/logging-review.md)을 따른다. 기록 복구와 본 실험 준비는 아직 완료되지 않았다.
