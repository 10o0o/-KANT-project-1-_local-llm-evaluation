# 로컬 LLM 코딩테스트 평가

Qwen과 Gemma가 생성한 Python 풀이를 COCI 공개 테스트 데이터로 실행·채점하고, 응답 품질과 실행 지표를 비교하는 프로젝트입니다. Cloud Luna 실행은 로컬 후보 선정과 분리해 비교합니다.

현재 진행 상태와 다음 한 작업은 [STATE](STATE.md), 유지보수 인계는 [작업 목록](docs/maintenance-handoff.md), 파일 책임과 현재 구조는 [architecture](docs/architecture.md)에서 확인합니다. 이 README는 실행 방법과 저장소의 큰 경계만 설명합니다.

현재 계획은 로컬 2모델 × 10문항 × 2회 = 40회, Cloud Luna 10문항 × 2회 = 20회입니다. 두 회차는 같은 문제·지시문·제공자별 설정으로 독립 요청하며 이전 답변이나 채점 결과를 전달하지 않습니다. 현재 확인된 중단 범위와 계획 전체, 생성 완료·채점 완료·품질 평가 완료는 서로 구분합니다.

```text
문제문 → 모델 호출 → 원본 응답·생성 지표·후보 저장
전체 생성 완료 → 모델 서버 종료 → 순차 일괄 채점 → 채점 세션 저장
```

학습 실습·실제 모델/Cloud 호출·후보 채점·설명 평가·집계·최종 선정은 직접 수행합니다. 명시적으로 승인된 유지보수의 문서·코드·모의 검증은 실제 실험 완료의 근거가 아닙니다. 저장소 경계는 [AGENTS.md](AGENTS.md)를 따릅니다.

## 설치와 실행 전제

모든 명령은 저장소 루트 `/home/jake/workspace/projects/kant/local-llm-evaluation`에서 실행합니다.

```bash
git clone https://github.com/10o0o/-KANT-project-1-_local-llm-evaluation.git local-llm-evaluation
cd -- local-llm-evaluation
uv sync --locked
```

Python 요구 범위는 `>=3.12`이며, `pyproject.toml`과 `uv.lock`이 패키지와 고정 의존성을 정의합니다. 모델 가중치, llama.cpp 런타임, 비밀키, COCI 테스트 데이터는 저장소에 넣지 않습니다.

문제 metadata의 `statement_path`, `problem_dir`, 시간·메모리 제한을 준비한 뒤 다음 명령으로 구조를 직접 확인합니다.

```bash
uv run llm-eval validate
```

검증 결과는 문제 목록·문제문·테스트 입출력 짝을 확인할 뿐, 모델 품질이나 실험 완료를 증명하지 않습니다.

## 표준 CLI

새 실행은 단일 `llm-eval` CLI를 사용합니다. 자세한 함수·호출자·테스트 매핑과 이전 명령의 제거 계획은 [architecture](docs/architecture.md)를 참고합니다.

```bash
# 별도 터미널에서 qwen36 또는 gemma4 서버를 시작
bash configs/llama.cpp/qwen36.sh

# 서버 준비 후 모델당 한 번 실행. warmup은 결과 파일을 만들지 않음
uv run llm-eval warmup --model qwen36

# 로컬 --round는 필수이며 두 회차는 독립 실행
uv run llm-eval generate local \
  --model qwen36 --problems all --round 1
uv run llm-eval generate local \
  --model qwen36 --problems all --round 2

# 자리를 비울 때 두 로컬 모델과 두 회차를 순차 처리
uv run llm-eval queue
```

Cloud는 로컬 생성·워밍업·큐·서버와 병행할 수 있습니다. 비교 대상은 `luna`와 `motif3` 두 제공자이며 `--model`은 필수입니다. 두 Cloud 모델은 잠금을 공유하므로 순차로 실행합니다. `--round`를 생략하면 Cloud는 Round 1을 사용합니다. 키는 모델별 환경 변수(`openai_secret_key`, `morph_api_key`)에서 읽으며 값은 출력·문서·결과에 저장하지 않습니다.

```bash
uv run --env-file ../project1-python-start/.env \
  llm-eval generate cloud --model luna --problems all --round 1
uv run --env-file ../project1-python-start/.env \
  llm-eval generate cloud --model luna --problems all --round 2

uv run llm-eval generate cloud --model motif3 --problems all --round 1
uv run llm-eval generate cloud --model motif3 --problems all --round 2
```

로컬·Cloud 전체 생성과 모델 서버 종료 후 오프라인 채점을 실행합니다.

```bash
uv run llm-eval judge batch --problems all --models all --rounds all
uv run llm-eval judge candidate --code path/to/candidate.py --problem <problem-id>
```

단일 응답과 과거 생성 한도 진단은 본 실험 집계와 분리합니다.

```bash
uv run llm-eval diagnose response
uv run llm-eval diagnose generation-limit --model qwen36
```

## 승인된 최종 트리

```text
.
├── configs/llama.cpp/       # qwen36.sh, gemma4.sh: 서버 실행 설정
├── data/coci/               # problems.json metadata와 사용자 준비 문제 자료
├── docs/                    # architecture, project, operations, history, sources
├── results/                 # 실행 시 생성되는 결과군과 README 안내
├── src/llm_eval/            # 단일 CLI와 local/cloud/judging/shared 패키지
├── tests/                   # 책임별 mock/fixture 및 합성 경계 테스트
├── .agents/skills/          # 명시적 요청 때만 쓰는 저장소 Notion journal skill
├── AGENTS.md                # 작업 경계와 보존 규칙
├── STATE.md                 # 확인된 진행 상태와 다음 한 작업
├── pyproject.toml           # package와 llm-eval console script
└── uv.lock                  # 고정 의존성
```

Python 세부 트리는 [architecture](docs/architecture.md)에 있습니다. `scripts/`와 provider별 호환 진입점은 제거했고, 진입점·진단·생성·채점 책임을 package 안에서 관리합니다.

## 실험 설정과 해석 경계

현재 실험 설정은 서버와 요청을 구분합니다. Qwen·Gemma 서버 Context는 65536, 기본 출력은 61440, reasoning budget은 53248, temperature는 0입니다. Qwen은 GPU layers all·CPU MoE 32, Gemma는 GPU layers auto·fit on·fit target 0을 사용하며 두 셸의 threads 16/24와 cache RAM 0을 보존합니다. 이 파일 설정만으로 과거 실행의 실제 적용이나 VRAM 적합성을 소급하지 않습니다. 세부 관측 근거는 [환경 문서](docs/operations/environment.md)를 따릅니다.

요청 전체 경과 시간, llama.cpp 내부 생성 속도, 모델 VRAM 관측, Cloud token/cost 추정은 서로 다른 지표입니다. 누락은 0으로 대체하지 않고 사유와 함께 기록합니다. Judge는 테스트별 시간과 stdout/stderr 합산 10 MiB 출력 제한을 적용하지만 메모리 제한·RSS·MLE를 구현하지 않습니다. 기록 의미와 한계는 [기록 구현 점검](docs/operations/recording.md)을 참고합니다.

## 결과 위치

```text
results/benchmark/<문제>/<모델>/round_<회차>/
├── response.json       # 원본 provider 응답이 저장된 경우
├── candidate.py        # 추출 코드가 있는 경우
└── result.json         # 요청·상태·지표·완료 표시

results/judging/<세션 ID>/
├── manifest.json
└── <문제>/<모델>/round_<회차>/judge.json
```

`pilot/`, `calibration/`, `diagnostics/`, `archive/`는 별도 의미를 가진 생성 파일군입니다. 폴더 존재만으로 실험·채점·학습 완료를 판단하지 않습니다. 생성 파일군의 이름과 집계 경계는 [결과 안내](results/README.md)에만 정리합니다.

## 문서 지도

| 문서 | 역할 |
| --- | --- |
| [architecture](docs/architecture.md) | 모든 관리 파일의 책임·호출자·테스트·제거된 CLI 매핑 지도 |
| [로컬 실행 안내](docs/operations/local-runbook.md) | 서버·워밍업·로컬 두 회차·큐·채점·모의 검증 |
| [Cloud 비교 안내](docs/operations/cloud-runbook.md) | Luna·Motif-3 독립 회차·모델별 키 로드·비용·채점 경계 |
| [실행 환경](docs/operations/environment.md) | 장비·버전·서버 설정의 관측 범위 |
| [기록 구현 점검](docs/operations/recording.md) | 지표·저장·누락값·Judge 한계 |
| [발제·평가·요구사항](docs/project/assignment.md) | 원문 기준·평가표·사용자 정의 조건 |
| [단계별 학습 안내](docs/project/learning-guide.md) | 사용자 직접 수행 순서와 완료 근거 |
| [정리 이력](docs/history/README.md) | 이전 경로와 Git 복원 정보 |
| [결과 안내](results/README.md) | 결과군 이름·집계 제외·채점 세션 의미 |
| [STATE](STATE.md) · [유지보수 인계](docs/maintenance-handoff.md) | 현재 상태·다음 행동·통합 기록 |

발제 원문과 `docs/sources/`의 snapshot은 원문 보존 대상입니다. 구조 정리 때문에 수정하지 않습니다.
