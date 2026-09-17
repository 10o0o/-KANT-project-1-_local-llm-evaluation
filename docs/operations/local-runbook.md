# 로컬 벤치마크 실행 안내

[README](../../README.md)의 Python·테스트 데이터 준비 후 현재 저장소 `/home/jake/workspace/projects/kant/local-llm-evaluation`의 저장소 루트에서 직접 실행한다. 현재 실행 상태와 종료 후 작업은 [STATE](../../STATE.md), [문서 정리 인계](../maintenance-handoff.md)를 따른다. 현재 전체 계획은 네 모델×10문항×2회인 80회이며, 이전 60회 계획은 계획 변경 이력으로 구분한다. 그 계획에서 생성된 현재 경로의 원본은 현재 80회에 포함한다. 이 안내의 명령을 정리한 것만으로 실행 완료를 뜻하지 않는다.

수동 실행과 자동 큐 중 한 경로를 사용한다. 진행 중인 로컬 작업이 있으면 별도의 로컬 생성·워밍업·큐·채점을 시작하지 않는다. [Cloud 10문항×2회](cloud-runbook.md)는 로컬 생성·워밍업·큐·서버와 어느 순서로든 병행할 수 있다. 전체 생성과 서버 종료 후 별도로 채점한다.

## 서버 실행

별도 터미널에서 사용할 모델 하나를 시작한다. 기본 경로가 설치 위치와 다르면 `LLAMA_ROOT`, `GEMMA4_MODEL_PATH` 또는 `QWEN36_MODEL_PATH`를 지정한다.

```bash
bash configs/llama.cpp/gemma4.sh
# Qwen을 실행할 때:
# bash configs/llama.cpp/qwen36.sh
```

서버 터미널에서 준비 완료를 확인한 뒤 워밍업을 실행한다. 두 서버는 `127.0.0.1:8080`을 공유하므로 모델 전환 시 기존 서버를 종료한다. 수동 실행에서는 서버 셸을 직접 사용하고 환경 JSON을 연결하지 않는다. 자동 큐 실행은 아래 별도 절차를 따른다.

| 서버 설정 | Qwen | Gemma |
| --- | --- | --- |
| API 모델 이름 | `qwen36` | `gemma4` |
| Context | 65536 | 65536 |
| 기본 출력 / reasoning / temperature | 61440 / 53248 / 0 | 61440 / 53248 / 0 |
| Parallel / Flash Attention | 1 / on | 1 / on |
| GPU layers | all | auto |
| Fit / fit target | 미지정 / 미지정 | on / 0 |
| CPU MoE layers | 32 | 미지정 |
| Generation / batch threads | 16 / 24 | 16 / 24 |
| Load mode | none | auto |
| Lazy mode | 미지정 | auto |
| RAM prompt cache | 0 MiB (비활성) | 0 MiB (비활성) |

미지정 옵션은 런타임 기본값을 따른다. 현재 Gemma 셸은 `--gpu-layers auto --fit on --fit-target 0 --load-mode auto --lazy-mode auto --threads 16 --threads-batch 24`를 사용한다. Qwen의 `--fit`은 미지정이다. 과거 `fit-target 1536` 값은 날짜가 있는 이력으로 보존하며 현재 표와 과거 실행 설정을 섞지 않는다. 이후 Qwen 진단의 로그 인용에는 기본 fit 수행과 parameter 변경 없음이 보고됐으며 [환경 근거](environment.md)에 구분해 기록했다. 표는 설정값이며 실제 적재 상태·VRAM 적합성은 직접 실행해서 확인한다.

## 워밍업 후 두 회차 평가

다른 터미널에서 실행한다. 아래는 Qwen 예시이며 Gemma는 `--model gemma4`로 바꾼다. 모든 명령은 저장소 루트에서 실행한다. 로컬 `--round 1/2`는 필수이며 두 회차는 독립 요청이다.

```bash
uv run llm-eval warmup --model qwen36

uv run llm-eval generate local \
  --model qwen36 --problems all --round 1

uv run llm-eval generate local \
  --model qwen36 --problems all --round 2
```

워밍업은 모델당 별도 짧은 입력으로 호출하고 완료 여부만 터미널에 표시한다. 파일 저장·환경 기록·성능 측정은 하지 않는다. 실패하면 오류를 그대로 전달한다. 워밍업은 본 실험 로컬 40회와 평균에서 제외한다. 요청은 출력 128·reasoning 64·temperature 0이다.

`--problems`에는 `all` 또는 `data/coci/problems.json`의 ID를 쉼표로 나열한다. 본 실험은 동일 문제문·지시문·생성 설정으로 두 번 독립 요청한다. 이전 답변이나 채점 결과는 전달하지 않으며 Round 1 없이 Round 2도 실행할 수 있다. 현재 작업 트리의 공통 요청에는 [reasoning 종료 메시지](../history/reasoning-budget-diagnostic.md)도 추가했다. 메시지 본문·소스 근거는 진단 문서에 정리했다. 새 로컬 성공·실패 기록에는 `generation_config.reasoning_budget_message`도 저장한다. 공통 요청의 `cache_prompt=false`와 서버의 `--cache-ram 0`은 유지한다. 여기서 독립 요청은 이전 답변을 전달하지 않는 절차를 뜻한다. 응답의 캐시 카운터는 해당 요청의 근거이며 전체 실험의 독립성을 단독으로 증명하지 않는다.

서버 설정 변경은 서버 재시작이 필요하다. Python 요청값은 다음 실행에 적용되므로 두 설정을 함께 확인한다. 실행할 모델과 서버를 직접 맞춘다. 환경 파일 연결·검증은 하지 않는다. 클라이언트 timeout은 3600초이며 자동 재시도는 꺼져 있다. 호출 실패는 기록한 뒤 중단하고, 같은 명령 재실행 시 보존된 실패 시도는 건너뛴다.

과거 calibration·diagnostic 실행기는 당시 실험용이다. 과거 Ollama 실습은 [정리 전 Git 이력](../history/README.md)에 보존했다.

## 자리를 비울 때: 로컬 두 모델 자동 생성

기존 로컬 생성기·워밍업·큐, 채점기와 모델 서버가 종료된 뒤 사용한다. Cloud 생성과는 병행할 수 있다. 현재 문제 저장 도중 중단하면 빈/부분 결과 폴더가 남을 수 있다. 예약기는 이런 폴더와 호출 실패를 자동 삭제하거나 재시도하지 않고 시작 전에 알려준다.

저장소 루트의 새 WSL 터미널에서 세션을 연다.

```bash
tmux new -s local-benchmark
```

세션 안에서 실행한다.

```bash
uv run llm-eval queue
```

순서는 Qwen 서버 시작·워밍업 → Qwen Round 1의 남은 문제 → Round 2 → Qwen 종료 → Gemma 서버 시작·워밍업 → Gemma Round 1 → Round 2 → Gemma 종료다. Cloud 호출과 채점은 하지 않는다. 동일 입력·설정의 완료 항목은 건너뛰며, 두 회차 모두 완료된 모델은 서버도 시작하지 않는다. 응답의 코드 미추출·출력 한도 종료는 생성 시도로 보존하고 다음 문제로 넘어간다.

Gemma 서버 셸은 **Gemma를 실제로 시작하는 시점의 내용**을 실행한다. Qwen 실행 중 Gemma의 GPU·fit·스레드 설정을 수정해도 전환 시 반영하며 예약기 내부에 복사한 옵션으로 덮어쓰지 않는다. 서버 셸은 foreground `exec` 방식과 별칭 `qwen36`·`gemma4`, `127.0.0.1:8080` 연결을 유지한다. 실제 서버 인수와 사용한 셸 사본·해시를 로그에 남긴다. 실행 후 파일 수정은 이미 실행 중인 서버에 적용되지 않는다.

Context·출력·reasoning을 수정할 때는 Python 요청값도 함께 확인한다. 서버 기본값과 Python 요청값은 다르며 요청 설정은 기존 생성기 값을 유지한다. Gemma의 실제 VRAM 적합성은 서버 시작 후 확인한다.

서버 준비는 기본 900초까지 기다리며 필요하면 `--startup-timeout-seconds 1800`으로 조정한다. 준비 상태·별칭·포트 소유권을 확인한 뒤 워밍업한다. 실패 시 전체 예약을 중단하고 큐가 직접 시작한 프로세스만 정리한다. 서버 종료가 60초 안에 끝나지 않으면 소유 프로세스를 강제 종료하고 다음 단계로 넘어가지 않는다.

`Ctrl+B` 다음 `D`로 tmux에서 분리하고, 아래 명령으로 다시 연결한다.

```bash
tmux attach -t local-benchmark
```

각 실행의 로그는 `logs/local_queue/<실행 ID>/`에 남는다. `queue.log`는 단계별 진행, `status.json`은 현재 단계·최종 상태·실패 이유, `<모델>.server.log`는 서버 출력, `<모델>.round_<회차>.log`는 문제별 생성 출력이다. 로그는 Git에서 제외한다. 중단 시 현재 문제의 부분 결과가 남을 수 있으며 원본은 그대로 보존한다.

프로세스·포트 검사는 시작 시 충돌을 확인한다. 로컬 생성·워밍업·큐는 `logs/.workload.lock`, Cloud 생성은 `logs/.cloud-workload.lock`을 사용한다. 일괄 채점·단일 후보 실행은 로컬→Cloud 순서로 두 잠금을 확보하며, 두 번째 획득 실패 시 첫 잠금을 반환한다. 서버는 잠금을 직접 획득하지 않고 프로세스 검사로 감지한다. 큐의 로컬 생성·워밍업 자식만 잠금 FD를 상속하고 파일 정체성·잠금 소유를 확인하며, 자식은 부모 잠금을 해제하지 않는다. 현재 root CLI와 이미 실행 중인 구형 script 이름, 서버를 검사하되 Cloud와 로컬 작업의 병행은 허용한다. 큐는 기존 로컬 작업·채점·서버·사용 중인 포트와 충돌하면 중단하며 발견한 프로세스에 신호를 보내지 않는다. 구형 script 감지는 제거된 명령을 다시 실행하거나 호환하는 기능이 아니다. 다른 checkout이나 구형 잠금을 사용하지 않는 작업의 동시 시작까지는 완전히 차단하지 않으며, 실제 FD 경쟁·상속·해제는 임시 저장소의 합성 프로세스로 검증했다. 큐 실행 중 별도 로컬 생성·채점은 시작하지 않는다. Cloud 생성은 병행할 수 있다. 전원을 연결하고 절전·최대 절전을 끈 상태에서 `Win+L`로 잠근다. tmux는 Windows 절전·재시작을 막지 않는다. 이 명령을 직접 실행하기 전에는 예약이 시작되지 않는다.

## 전체 생성 완료 후 기준 채점

로컬·Cloud 생성이 모두 끝나면 모델 서버 터미널에서 서버를 종료한 뒤 기준 채점을 실행한다. 실행 중인 생성기·서버는 이 명령이 자동 종료하지 않는다. 기준 `judge batch`는 생성 원본을 공식 1배 시간 제한으로 채점하는 기준 세션이며, 이후 제한 재평가·보조 수정은 별도 평가 명령으로 실행한다. 생성·채점 분리 변경 전에 시작한 프로세스는 당시 코드를 사용하므로 현재 파일만으로 실행 중 동작을 소급 판단하지 않는다.

```bash
uv run llm-eval judge batch --problems all --models all --rounds all
```

예전 `scripts/run_benchmark.py`, `scripts/run_judge.py`와 표준 script 이름은 제거됐다. 새 실행은 [architecture](../architecture.md)의 `uv run llm-eval` 명령만 사용한다. workload process 감지는 이미 실행 중인 구형 프로세스를 식별할 수 있지만, 제거된 script를 다시 호출하거나 호환하는 기능은 제공하지 않는다.

`--problems`는 `all` 또는 전체 문제 ID, `--models`는 `all` 또는 `qwen36,gemma4,luna,motif3`, `--rounds`는 `all` 또는 `1,2`를 받는다. 예를 들어 Tezina만 선택하려면 `--problems coci_2025_2026_c5_tezina`를 사용한다. Luna와 Motif-3도 round 1·2를 대상으로 한다. 일괄 채점의 `--rounds` 기본값은 `all`이며 두 회차를 모두 선택한다.

기존 판정 유무와 관계없이 저장된 원본 후보를 순차 채점한다. 후보가 `extracted_code`와 다르거나 생성 폴더가 불완전하면 시작 전에 중단한다. 수정본 한 개의 검증에는 `uv run llm-eval judge candidate --code <path> --problem <id>`를 사용한다.

정상 저장을 마친 생성 기록은 `record_complete=true`, `judge=null`로 저장한다. 후처리가 실패하면 가능한 범위에서 `record_complete=false`와 오류 단계를 남긴다. 생성 기록 완료는 모델의 정답 또는 API 응답의 완전한 종료를 뜻하지 않는다. 동일 입력·설정의 구형 채점 완료 기록과 새 생성 완료 기록, 호출 실패는 재호출하지 않는다.

채점 결과는 `results/judging/<세션 ID>/<문제>/<모델>/round_<회차>/judge.json`과 세션 `manifest.json`에 저장한다. 재실행마다 새 세션을 만들며 생성 원본과 이전 채점 결과는 덮어쓰지 않는다. 상세 필드와 미생성·중단 처리는 [결과 안내](../../results/README.md#일괄-채점-세션)를 따른다. 이 기준 세션 자체에는 유효 제한 2배나 설명 점수를 반영하지 않는다.

채점 중에는 새로운 생성 작업이나 다른 무거운 작업을 시작하지 않는다. 채점 CLI는 저장소별 로컬·Cloud 잠금을 모두 사용하고 Linux/WSL의 `/proc`에서 root CLI, 이미 실행 중인 구형 script 이름과 `llama-server`를 검사한다. 잠금을 모르는 외부 작업이나 다른 저장소가 동시에 시작되는 경우까지 완전히 차단하지는 않는다. 별도 Windows 프로세스나 다른 실행 방식의 부하까지 검증하지는 않는다. 각 테스트는 실제 경과 시간과 stdout·stderr 합산 10 MiB 출력 한도를 적용하며 먼저 발생한 자원을 `TLE` 또는 `OLE`로 기록한다. 채점 인프라·처리 예외는 `JUDGE_ERROR`로 기록한다.

## 프로젝트 평가 후처리

기준 채점 세션을 만든 뒤 [평가 실행 안내](evaluation.md)의 순서로 평가를 진행한다. 평가 기준은 생성 시작 후 확정됐으므로 사전등록으로 표시하지 않는다. 열 문항 모두 공식 1배 제한의 원본 평가와 최소 수정 보조 대상이다. 기준 세션의 개별 테스트 중 `TLE`가 있으면 해당 문항 전체를 유효 2배 제한으로 다시 실행한다. 네 개의 scoring 문항의 2배 결과는 scoring에 반영하고, 나머지 여섯 문항의 2배 결과는 diagnostic으로 보존한다. 생성 프롬프트의 공식 시간·메모리 제한은 바꾸지 않는다.

```bash
uv run llm-eval evaluate prepare --baseline <세션 ID>
uv run llm-eval evaluate run --evaluation <평가 ID> --kind limits
```

각 `review.json`에 설명 점수와 보조 수정 판단을 직접 입력한 뒤, 필요할 때만 수정 실행을 이어 간다.

```bash
uv run llm-eval evaluate run --evaluation <평가 ID> --kind repairs
uv run llm-eval evaluate report --evaluation <평가 ID>
```

성공 호출의 `response_elapsed_seconds` 평균은 코드 유무와 무관하게 계산하고, `CALL_ERROR`의 실패 시간은 별도 n으로 기록한다. `NO_CODE`는 정상 수신 응답이면 설명 평가에 포함한다. 평가 결과·리뷰·보고서는 `results/evaluation/<평가 ID>/`에 새로 저장하며 기준 세션과 생성 원본을 수정하지 않는다.

## 중단과 재개

수동 생성기는 같은 문제·모델·회차의 요청과 설정이 같은 완료 시도를 건너뛴다. 보존한 호출 실패도 자동 재시도하지 않는다. 로컬은 성공 기록의 원본 응답 JSON 존재·형식과 추출 코드/후보 일치를 확인한다. 자동 큐는 저장된 호출 실패나 불완전한 폴더가 있으면 시작 전 중단한다. 부분 폴더·실패 기록을 삭제해 재호출하지 말고 원본을 보존한 채 확인한다.

Cloud도 원본 JSON·후보와 저장된 응답 메타데이터의 일관성을 확인한다. 응답 없는 호출 예외와 오류 응답 수신을 구분한다. 모든 응답 필드의 의미적 일치를 보증하지는 않는다. 동작과 남은 검증은 [기록 구현 점검](recording.md), [구조 개선 인계](../maintenance-handoff.md#현재-상태와-다음-행동)에 남겼다.

## 모의 검증

벤치마크와 채점이 끝난 뒤 필요할 때 직접 실행한다.

```bash
uv run python -m unittest discover -s tests -v
```

모델 응답·GPU 조회·subprocess를 모의 처리한다. 모의 검증과 합성 프로세스 경계 검증의 최신 수치·통과·건너뜀 상태는 [작업 인계](../maintenance-handoff.md#현재-상태와-다음-행동)의 현재 표를 따른다. 이 검증은 실제 생성·Judge·모델 품질·VRAM 적합성·본 실험 완료를 증명하지 않는다. 합성 프로세스 검증은 `LLM_EVAL_RUN_PROCESS_TESTS=1`을 명시한 승인된 별도 경로에서만 수행한다. 실행기와 검증 로그 위치는 인계 문서에 남겼다.
