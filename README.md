# 로컬 LLM 코딩테스트 평가

Qwen과 Gemma가 생성한 Python 풀이를 공개 테스트 데이터로 실행·채점하고 결과를 비교하는 프로젝트입니다. 정답 여부와 함께 풀이 설명, 추론 내용, 생성 속도를 살펴보며 코딩테스트 풀이에 적합한 로컬 모델을 찾습니다.

COCI에서 선정한 10문항을 사용합니다. 현재 실행기는 모델 하나에 문제 하나를 요청하고, 응답·생성 지표와 추출 코드를 저장합니다. 채점은 전체 생성과 모델 서버 종료 후 별도로 수행합니다. AI의 원본 조회에서 확인한 중단 기록은 Qwen 20건·Luna 10건·Gemma Round 1 5건, 합계 35건이며 모두 호출 성공이다. Qwen의 `skijanje` 2건은 코드 미추출이다. 이는 계획한 60회 완료나 품질·채점 완료를 뜻하지 않는다.

```text
문제문 → 모델 호출 → 응답·생성 지표·Python 코드 저장
전체 생성 완료 → 모델 서버 종료 → 순차 일괄 채점 → 채점 회차별 저장
```

현재 진행 근거와 다음 한 작업은 [STATE](STATE.md), 문서 정리와 종료 후 인계는 [작업 목록](docs/maintenance-handoff.md)에서 확인한다.

현재 로컬 저장소는 `/home/jake/workspace/projects/kant/local-llm-evaluation`이다. 운영 명령은 저장소 루트에서 실행한다. 생성 기록 35건은 저장소에 보존했고 모델 가중치·비밀 파일·테스트 데이터는 포함하지 않는다. Cloud `--round`는 기본 1이며 2를 선택할 수 있고, 로컬 생성은 `--round 1` 또는 `--round 2`를 명시한다. 통합 검증·게시 상태는 [인계 문서](docs/maintenance-handoff.md#현재-상태와-다음-행동)를 따른다.

학습 실습·실제 모델 호출·채점·평가는 직접 수행한다. 명시적으로 맡긴 유지보수의 AI 구현·정적/모의 검증은 별도 기록한다. 범위는 [튜터 지침](AGENTS.md)에 따른다.

## 발제와 현재 수행 기준

| 구분 | 기준 |
| --- | --- |
| 발제 원문 | Ollama, 서로 다른 로컬 2모델 × 10문항 × 2회 = 40회, Cloud 공통 5문항 × 1회 |
| 현재 수행 | 튜터에게 허락받아 llama.cpp로 전환했다. Qwen·Gemma의 독립 반복 40회와 Cloud Luna 전체 10문항 × 2회 = 20회를 구분한다. 로컬과 Cloud는 제공자·생성 설정이 다르며 문제 목록·반복 수·독립성만 공통으로 맞춘다. 일부 결과를 본 뒤 Cloud 범위를 확장한 경과를 사전 선정으로 소급하지 않는다. 전체 계획은 60회이며 Cloud는 최종 로컬 후보 선정에서 제외한다. AI의 원본 조회에서 확인한 중단 기록은 35건이고, Round 2 지원은 구현돼 있으나 실제 완료·Judge·최종 비교는 별도 근거가 필요하다. |
| 사용자 정의 평가 | 원본 유효 정답 12/20(60%) 통과선과 선정 순서는 [요구사항](docs/project/requirements.md)을 따른다. 호출 성공 수/시도 수·지표별 n도 별도로 유지한다. |
| 개인 필수 | 기본 과제 이후 세 번째 로컬 모델·Transformers 직접 실행·동일 모델 양자화 비교·임베딩 실습 4개를 수행한다. [개인 필수 실습](docs/project/learning-guide.md#발제-선택사용자-필수)은 발제 공통 필수와 구분한다. |

생성 기록 완료, 채점 완료, 설명 평가·집계·최종 선정 완료는 서로 다르다. 설명 평가·집계·최종 선정의 완료 근거는 아직 확인하지 않았다.

## 실행 환경

- 확인한 Python 환경은 3.12, 패키지 요구 범위는 `>=3.12`; uv 사용
- `--reasoning-budget`을 지원하는 llama.cpp 빌드와 `llama-server`
- 해당 llama.cpp에서 로딩할 수 있는 Qwen·Gemma GGUF 가중치
- COCI 문제별 테스트 입력·정답 파일

확인한 장비·버전·모델 파일과 실제 관측 범위는 [실행 환경과 측정 근거](docs/operations/environment.md)에 정리했습니다. 서버 스크립트의 GPU 설정은 이 환경에서 사용한 값이므로 장비에 맞게 조정해야 합니다. 모델 가중치, llama.cpp 런타임, 테스트 데이터는 저장소에 포함하지 않습니다.

## 설치와 실행

### 1. Python 환경 준비

저장소를 내려받은 뒤 루트에서 실행합니다.

```bash
git clone https://github.com/10o0o/-KANT-project-1-_local-llm-evaluation.git local-llm-evaluation
cd -- local-llm-evaluation
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

선정 문항의 영어 문제문은 같은 JSON의 `statement_path`에 있습니다. 모델에는 설명·입출력 조건·제약·예제를 전달하고, 제목·대회 정보·난이도 등 평가용 메타데이터는 분리합니다. 시간·메모리 제한은 `problems.json`에서 읽어 문제 바로 위의 실행 제한 블록으로 로컬·Cloud에 동일하게 전달합니다. 원본 PDF와 테스트 데이터의 출처는 COCI이며, 이 저장소가 해당 자료에 별도의 라이선스를 부여하지 않습니다.

문제문에 포함된 그림은 Markdown에서 확인할 수 있습니다. 현재 호출기는 텍스트만 전송하므로 이미지 파일 자체는 모델에 전달되지 않습니다.

데이터 준비 후 다음 검증기를 직접 실행한다. 문제 목록·문제문·테스트 입출력 짝을 확인하며, 문제의 텍스트 적합성이나 모델 품질 판정을 대신하지 않는다. 최종 `Validation PASSED`와 종료 코드를 확인한다.

```bash
uv run python scripts/validate_dataset.py
```

### 3. 생성과 채점

1. [로컬 실행 안내](docs/operations/local-runbook.md): 서버·워밍업·독립 두 회차를 수동 실행하거나 자동 큐를 사용한다.
2. [Cloud 비교 안내](docs/operations/cloud-runbook.md): 로컬 측정 종료 후 Luna 10문항을 두 회차 독립 실행한다. 키 로드 방법과 로컬과의 설정 차이는 해당 안내를 따른다.
3. [일괄 채점 절차](docs/operations/local-runbook.md#전체-생성-완료-후-일괄-채점): 로컬·Cloud 전체 생성과 모델 서버 종료 후 직접 채점한다.

생성·채점의 표준 진입점은 `scripts/run_local_benchmark.py`와 `scripts/run_batch_judge.py`다. 기존 `run_benchmark.py`·`run_judge.py` 명령은 이전 사용자를 위한 호환 진입점로 유지하며 새 절차에서는 표준 진입점을 사용한다.

## 결과 위치와 해석

```text
results/benchmark/<문제>/<모델>/round_<회차>/
├── response.json   # 원본 API 응답이 저장된 경우
├── candidate.py    # 추출 코드가 있는 경우
└── result.json     # 호출 상태·요청·응답·생성 지표·기록 완료 여부

results/judging/<세션 ID>/
├── manifest.json
└── <문제>/<모델>/round_<회차>/judge.json
```

로컬과 Luna는 각각 두 회차이며, 계획한 본 실험은 로컬 40회와 Cloud 20회, 총 60회다. 현재 전달된 35건은 일시정지 범위로 별도 표시하고 나머지 계획을 완료로 소급하지 않는다. 실패·부분 기록에서는 파일 구성이 다를 수 있다. 판정은 선택한 채점 세션을 원본 run ID와 연결해 읽고, 원본과 수정본·pilot·과거 embedded 판정을 섞지 않는다. 세부 필드·판정·집계 제외 이력은 [결과 안내](results/README.md)를 따른다. 현재 폴더의 존재만으로 실험 완료를 판단하지 않는다.

## 저장소와 문서

| 위치 | 역할 |
| --- | --- |
| `configs/llama.cpp/` | 모델 서버 실행 셸 |
| `scripts/` | 생성·워밍업·큐·채점·데이터 검증 진입점과 `diagnostics/` 아래 과거 진단 |
| `src/llm_eval/local/` | 로컬 호출·생성·워밍업·큐; `server.py`는 서버 탐색, `metrics.py`는 관측·지표 |
| `src/llm_eval/cloud/` | Cloud 호출·생성·사용량·비용 |
| `src/llm_eval/judging/` | 후보 채점·일괄 처리; `process.py`는 아직 미연결인 출력 제한 도구 |
| `src/llm_eval/shared/` | 프롬프트·문제 읽기·코드 추출·결과 경로·저장·파일 검사·작업 잠금 |
| `tests/local/`, `cloud/`, `judging/`, `shared/` | 동일 책임별 모의 테스트 |
| `docs/project/`, `operations/`, `history/`, `sources/` | 과제 기준·운영 절차·과거 이력·원문 스냅샷 |
| [문제 목록](data/coci/problems.json) | 선정 10문항의 ID·문제문/테스트 경로·실행 제한 |
| [결과 안내](results/README.md) | 생성·채점 결과와 pilot·진단·보관 기록의 구분 |
| [요구사항](docs/project/requirements.md) · [모델 조사](docs/project/model-candidates.md) | 사용 사례·선정 기준·후보 정보 |
| [실행 환경](docs/operations/environment.md) · [기록 구현 점검](docs/operations/recording.md) | 장비·설정·측정의 확인 범위와 한계 |
| [발제 원문](docs/project/assignment.md) · [평가표](docs/project/assignment-rubric.md) · [단계별 안내](docs/project/learning-guide.md) | 과제 기준·학습 절차 |
| [정리 이력](docs/history/README.md) | 과거 파일 위치와 복원 방법 |
| [STATE](STATE.md) · [작업 인계](docs/maintenance-handoff.md) | 현재 근거·다음 한 작업·완료/보류 목록 |
| [튜터 지침](AGENTS.md) | 직접 수행 원칙과 승인된 AI 유지보수·정적/모의 검증 범위 |

과거 calibration·diagnostic 실행기는 당시 실험용이며 본 실험 경로와 구분한다. 선정 10문항 외 Slaganje는 calibration에 사용한 자료다. 모의 검증 명령은 [로컬 안내](docs/operations/local-runbook.md#모의-검증)에 있다.
