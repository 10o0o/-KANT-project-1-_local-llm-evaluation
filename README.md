# 로컬 LLM 코딩테스트 평가

코딩테스트를 풀 때 쓸 로컬 LLM을 하나 고르기 위한 실험 저장소입니다.

답변이 그럴듯한지만 보지 않습니다. COCI 공개 문제를 풀게 한 뒤 모델이 생성한 Python 코드를 실제 테스트 데이터로 실행해 AC·WA·TLE·RE·NO_CODE까지 받아 봅니다. 채점을 외부 사이트에 맡기지 않으려고 공식 테스트 데이터가 공개된 대회를 골랐고, 로컬 Judge를 직접 구현했습니다.

비교 대상은 로컬 2개(Qwen3.6, Gemma4)와 Cloud 2개(Luna, Motif-3)입니다. **Cloud는 운영 방식을 판단하는 별도 축이며 최종 로컬 선정에는 합치지 않습니다.**

```text
문제문 + 공식 시간·메모리 제한
  → 모델 호출 → 원본 응답·생성 지표·추출 코드 저장   (round 1·2 독립 반복)
  → 전체 생성 완료 → 모델 서버 종료
  → 순차 일괄 채점 → 채점 세션 저장
```

생성과 채점을 붙여 두면 채점 프로세스가 모델 서버와 CPU를 다투어 TLE 측정이 흔들립니다. 그래서 모든 생성이 끝나고 서버를 내린 뒤에만 채점합니다.

## 실험 범위

모델당 10문항 × 2회 = 20회, 네 모델 합쳐 **80회**가 계획입니다. 두 회차는 같은 문제문과 제공자별 설정으로 새로 요청하며 이전 답변이나 채점 결과를 넘기지 않는 독립 반복입니다.

네 모델이 공유하는 것은 문제 목록·반복 수·독립성뿐입니다. 제공자마다 API 계열과 생성 설정이 달라 토큰 예산이나 temperature까지 같은 조건이라고 적지 않습니다. Luna와 Motif-3도 각각 20회의 분모를 따로 두고 하나의 Cloud 집계로 합치지 않습니다.

계획 횟수와 완료 건수는 다릅니다. 생성 완료·채점 완료·품질 평가 완료도 각각 구분합니다. 현재 진행 상태는 [STATE](STATE.md)에서 확인합니다.

## 설치

모든 명령은 저장소 루트에서 실행합니다.

```bash
git clone https://github.com/10o0o/-KANT-project-1-_local-llm-evaluation.git local-llm-evaluation
cd -- local-llm-evaluation
uv sync --locked
```

Python은 `>=3.12`가 필요하고, 패키지와 고정 의존성은 `pyproject.toml`·`uv.lock`이 정의합니다. 모델 가중치, llama.cpp 런타임, API 키, COCI 테스트 데이터는 저장소에 넣지 않습니다. 각자 준비한 뒤 `data/coci/problems.json`의 `statement_path`·`problem_dir`과 시간·메모리 제한이 실제 파일과 맞는지 먼저 확인합니다.

```bash
uv run llm-eval validate
```

이 명령은 문제 목록과 문제문·테스트 입출력 짝이 제자리에 있는지만 봅니다. 모델 품질이나 실험 완료와는 무관합니다.

## 실행

### 로컬 생성

서버는 별도 터미널에서 셸로 띄웁니다.

```bash
bash configs/llama.cpp/qwen36.sh     # 또는 gemma4.sh
```

서버가 준비되면 모델당 한 번 워밍업하고 회차별로 생성합니다. 워밍업은 결과 파일을 만들지 않으며 본 실험 집계에서 제외합니다.

```bash
uv run llm-eval warmup --model qwen36

uv run llm-eval generate local --model qwen36 --problems all --round 1
uv run llm-eval generate local --model qwen36 --problems all --round 2
```

로컬은 `--round`가 필수입니다. 자리를 비울 때는 두 모델과 두 회차를 순차로 처리하는 큐를 씁니다.

```bash
uv run llm-eval queue
```

### Cloud 생성

Cloud는 로컬 생성·워밍업·큐·서버와 병행할 수 있습니다. 다만 두 Cloud 모델은 잠금을 공유하므로 서로는 순차로 실행합니다.

`--model`은 필수입니다. 유료 호출의 대상을 기본값으로 추론하지 않기 위해서입니다. 키는 모델별 환경 변수(`openai_secret_key`, `morph_secret_key`)에서 읽으며 값은 출력·문서·결과에 저장하지 않습니다.

```bash
uv run llm-eval generate cloud --model luna   --problems all --round 1
uv run llm-eval generate cloud --model luna   --problems all --round 2
uv run llm-eval generate cloud --model motif3 --problems all --round 1
uv run llm-eval generate cloud --model motif3 --problems all --round 2
```

키를 `.env` 파일로 관리한다면 `uv run --env-file <경로> llm-eval ...` 형태로 넘깁니다. `.env`는 저장소에 포함하지 않습니다.

### 채점

로컬·Cloud 생성을 모두 마치고 모델 서버를 내린 뒤 실행합니다.

```bash
uv run llm-eval judge batch --problems all --models all --rounds all
```

원본 후보를 고친 복사본을 따로 확인할 때는 `candidate` 모드를 씁니다. 이 결과는 모델의 원본 판정과 섞지 않고 보조 평가로만 씁니다.

```bash
uv run llm-eval judge candidate --code path/to/candidate.py --problem <problem-id>
```

### 진단

단일 응답 확인과 생성 한도 진단은 본 실험 집계와 분리합니다.

```bash
uv run llm-eval diagnose response
uv run llm-eval diagnose generation-limit --model qwen36
```

## 결과 위치

```text
results/benchmark/<문제>/<모델>/round_<회차>/
├── response.json       # 원본 provider 응답
├── candidate.py        # 추출 코드가 있을 때만
└── result.json         # 요청·생성 설정·호출 상태·지표·추출 코드

results/judging/<세션 ID>/
├── manifest.json
└── <문제>/<모델>/round_<회차>/judge.json
```

모델 폴더는 `qwen36`·`gemma4`·`luna`·`motif3`입니다. `result.json`에는 응답만이 아니라 요청 messages와 생성 설정, 호출 성공·실패 상태까지 함께 남깁니다. 나중에 "이 결과가 어떤 조건에서 나왔는지"를 파일만 보고 알 수 있게 하기 위해서입니다.

측정하지 못한 값은 0으로 채우지 않고 사유와 함께 `null`로 남깁니다. 예를 들어 상주 llama.cpp 서버는 요청별 모델 로딩 시간을 노출하지 않으므로 `model_load_seconds`는 `null`이고 `model_load_reason`에 그 이유가 들어갑니다.

`pilot/`, `calibration/`, `diagnostics/`, `archive/`는 각각 다른 의미를 가진 파일군입니다. 설정을 바꿀 때마다 이전 결과를 본 실험에서 내려 보존한 것들이라, 폴더가 있다는 것만으로 실험·채점 완료를 판단하면 안 됩니다. 이름별 의미와 집계 경계는 [결과 안내](results/README.md)에 정리했습니다.

## 저장소 구조

```text
.
├── configs/llama.cpp/       # qwen36.sh, gemma4.sh — 서버 실행 설정
├── data/coci/               # problems.json metadata와 준비한 문제 자료
├── docs/                    # architecture, project, operations, history, sources
├── results/                 # 실행하면 생기는 결과군
├── src/llm_eval/            # 단일 CLI와 local/cloud/judging/shared 패키지
├── tests/                   # 책임별 mock·fixture와 합성 경계 테스트
├── AGENTS.md                # 작업 경계와 보존 규칙
├── STATE.md                 # 확인된 진행 상태와 다음 한 작업
├── pyproject.toml           # package와 llm-eval console script
└── uv.lock                  # 고정 의존성
```

운영 명령은 `uv run llm-eval`과 같은 구현인 `python -m llm_eval` 둘뿐입니다. 예전에는 `scripts/` 아래에 진입점이 열 개 넘게 흩어져 있었는데, 문서에 적은 명령과 실제 쓰는 명령이 어긋나기 시작해 전부 패키지 안으로 합쳤습니다. 파일별 책임과 호출 관계, 관련 테스트는 [architecture](docs/architecture.md)에 매핑해 두었습니다.

## 실험 설정과 해석 경계

서버와 요청 설정을 구분해 기록합니다. 두 로컬 모델의 서버 Context는 65,536, 기본 출력 61,440, reasoning budget 53,248, temperature 0입니다. 배치는 다릅니다. Qwen은 `--gpu-layers all --n-cpu-moe 32`에 threads 16 / batch 24로 직접 고정했고, Gemma는 `--gpu-layers auto --fit on --fit-target 0`으로 auto fit에 맡겼습니다. 두 셸 모두 `--cache-ram 0`입니다.

이 파일 값만으로 과거 실행의 실제 적용 조건이나 VRAM 적합성을 소급하지는 않습니다. 특정 실행에 무엇이 적용됐는지는 그 실행의 `result.json`과 서버 로그로 따로 확인합니다. 관측 범위와 미확인 항목은 [실행 환경](docs/operations/environment.md)에 정리했습니다.

지표도 서로 다른 것을 섞지 않습니다. 요청 전체 경과 시간, llama.cpp 내부 생성 속도, GPU 사용량 관측, Cloud 토큰·비용 추정은 각각 다른 값입니다. 특히 GPU 사용량은 장치 전체 관측값이고 프로세스별 값은 조회되지 않아 사유와 함께 `null`로 남아 있으므로, 모델 단독 사용량으로 읽으면 안 됩니다.

Judge는 테스트별 시간 제한과 stdout·stderr 합산 10 MiB 출력 제한을 적용합니다. **메모리 제한 강제·RSS 측정·MLE 판정은 구현하지 않았습니다.** 따라서 AC는 보유한 테스트를 통과했다는 뜻이지 메모리 제한 준수를 증명하지 않습니다. 기록의 의미와 한계는 [기록 구현 점검](docs/operations/recording.md)을 참고합니다.

## 작업 경계

조사·구현·실험·채점·평가는 직접 수행합니다. AI에는 명시적으로 맡긴 범위만 맡기며, 그 범위에서 나온 문서·코드·모의 검증을 실제 실험 완료의 근거로 쓰지 않습니다. 자세한 규칙은 [AGENTS.md](AGENTS.md)를 따릅니다.

## 문서 지도

| 문서 | 역할 |
| --- | --- |
| [STATE](STATE.md) | 확인된 진행 상태와 다음 한 작업 |
| [architecture](docs/architecture.md) | 파일별 책임·호출자·테스트 매핑 |
| [로컬 실행 안내](docs/operations/local-runbook.md) | 서버·워밍업·두 회차·큐·채점 절차 |
| [Cloud 비교 안내](docs/operations/cloud-runbook.md) | Luna·Motif-3 실행 조건, 모델별 키 로드, 비용 경계 |
| [실행 환경](docs/operations/environment.md) | 장비·버전·서버 설정의 관측 범위와 미확인 항목 |
| [기록 구현 점검](docs/operations/recording.md) | 지표·저장·누락값·Judge 한계 |
| [요구사항과 평가 기준](docs/project/requirements.md) | 사용 사례, 60% 통과선, 선정 순서, 설명 정확성 기준 |
| [모델 후보 조사](docs/project/model-candidates.md) | 후보 비교표, Model Card·License, 제외한 후보 이력 |
| [발제 원문](docs/project/assignment.md) · [평가표](docs/project/assignment-rubric.md) | 과제 기준과 사용자 정의 조건의 구분 |
| [단계별 학습 안내](docs/project/learning-guide.md) | 직접 수행 순서와 완료 근거 |
| [결과 안내](results/README.md) | 결과군 이름·집계 제외·채점 세션 의미 |
| [정리 이력](docs/history/README.md) | 이전 경로와 Git 복원 정보 |
| [유지보수 인계](docs/maintenance-handoff.md) | 통합·검증 기록과 인계 사항 |
