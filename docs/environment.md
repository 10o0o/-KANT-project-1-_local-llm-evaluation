# 실행 환경과 측정 근거

2026-09-16 12:22 KST 기준 AI의 읽기 전용 조회와 저장 결과 점검을 참고해 정리했다. 환경 세션·자동 환경 JSON은 만들지 않는다. 현재 장비·파일·프로세스 관측이며 과거 모든 실행의 환경을 증명하지 않는다.

## 장비와 소프트웨어

| 항목 | 확인값 | 근거·범위 |
| --- | --- | --- |
| CPU | Intel Core Ultra 9 275HX | `/proc/cpuinfo`의 model name |
| 설치 시스템 RAM | 34,359,738,368 bytes = 32 GiB | Windows `Get-CimInstance Win32_PhysicalMemory`의 Capacity 합계 |
| Windows 보고 물리 메모리 | 33,752,997,888 bytes, 약 31.43 GiB | `Win32_ComputerSystem.TotalPhysicalMemory`; 설치 모듈 용량과 구분 |
| Linux 보고 메모리 | MemTotal 26,670,756 kB, 약 25.44 GiB | `/proc/meminfo`; WSL 게스트가 보고하는 총량이며 `.wslconfig`의 메모리 한도나 모델 RAM 사용량이 아님 |
| OS | Ubuntu 26.04.1 LTS / WSL2 | `/etc/os-release`, 커널 `6.18.33.2-microsoft-standard-WSL2`; Windows 호스트 OS 버전은 미확인 |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU | Skare 결과의 `metrics.memory.devices`; 장치 총량 8151 MiB |
| Python | 3.12.14 | 프로젝트 `.venv/bin/python`의 `sys.version` |
| uv | 0.12.5 | `uv --version` |
| 주요 설치 패키지 | openai 3.8.0, httpx 0.28.1, pydantic 2.13.5 | 프로젝트 가상환경의 `importlib.metadata.version`; 선언·고정 의존성은 [pyproject.toml](../pyproject.toml)과 [uv.lock](../uv.lock) 참고 |

시스템 RAM 총량과 실제 모델 RAM 사용량은 다르다. 모델의 시스템 RAM 사용량은 이번에 측정하지 않았다.

## 런타임과 모델 파일

- llama.cpp 소스 위치: `$HOME/workspace/local-llm/runtimes/llama.cpp`
- 소스 커밋: `4c9233c034fc450dcf34c7c0988aebe6da5cdf1a`. 해당 소스 저장소의 `git status --short` 출력은 비어 있었다.
- 현재 Qwen 프로세스 실행 파일: 위 경로의 `build/bin/llama-server`.
- 저장된 Skare 응답의 `system_fingerprint`: `b10975-4c9233c03`. 이는 응답이 보고한 빌드 표식이며 현재 소스 상태·바이너리 해시·GGUF 해시와 각각 구분한다. 바이너리 해시는 미확인이다.

모델 경로는 `$HOME/workspace/local-llm/models/` 기준이다. 파일 크기는 현재 로컬 파일의 `stat` 조회값으로 실행 산출물 구분에 사용한다. [모델 조사표](models.md)의 배포 문서상 크기를 대체하지 않는다.

| 모델 별칭 | 파일 경로 | 바이트 크기 | 양자화 확인 범위 | SHA-256 |
| --- | --- | --- | --- | --- |
| qwen36 | `qwen3.6-35b-a3b-q4_k_m/model.gguf` | 20,419,565,568 | 경로·선택 구성은 Q4_K_M, GGUF 내부 메타데이터는 미확인 | 이번 작업에서 미계산 |
| gemma4 | `gemma4-26b-a4b-it-q4_k_m/model.gguf` | 16,796,015,136 | 경로·선택 구성은 Q4_K_M, GGUF 내부 메타데이터는 미확인 | 이번 작업에서 미계산 |

파일명·크기만으로 파일 내용의 동일성을 확정하지 않는다. 과거 Ollama digest를 현재 GGUF 식별값으로 재사용하지 않는다.

## 설정값과 실제 적용 근거

서버 설정 원본은 [Qwen 셸](../configs/llama.cpp/qwen36.sh)·[Gemma 셸](../configs/llama.cpp/gemma4.sh), 공통 설정표는 [README](../README.md#3-서버-실행)에 있다. Context는 서버 설정이고, temperature·출력 한도·reasoning·cache_prompt는 요청에도 명시한다.

현재 실행 중인 Qwen의 `/proc/<pid>/cmdline`에서 다음 인수를 확인했다. 이 조회는 프로세스를 재시작하거나 모델을 호출하지 않았다.

```text
--model $HOME/workspace/local-llm/models/qwen3.6-35b-a3b-q4_k_m/model.gguf
--alias qwen36 --host 127.0.0.1 --port 8080
--ctx-size 12288 --n-predict 8192 --parallel 1
--gpu-layers all --n-cpu-moe 32 --load-mode none --flash-attn on
--temp 0 --reasoning on --reasoning-budget 2048
--threads 16 --threads-batch 24 --cache-ram 0
```

실제 인수의 홈 경로는 위 표기처럼 축약했다. Qwen 인수는 현재 셸과 일치하지만 `/props`와 시작 로그를 이번에 조회하지 않아 유효 Context·실제 텐서 적재 상태까지 확인한 것은 아니다. `all`과 CPU MoE 32를 단순 GPU 적재 비율로 환산하지 않는다. Gemma는 셸 설정만 확인했으며 현재 실행 인수·실제 적재 상태는 미확인이다. `--fit`은 미지정이며 동작을 변경하지 않았다.

저장된 Skare 요청은 temperature 0, max_tokens 8192, reasoning_budget_tokens 2048, cache_prompt false다. 환경 세션 연결이 없으므로 현재 프로세스 관측을 해당 요청 시점의 모든 실행 조건에 대한 증명으로 사용하지 않는다.

## 결과 해석과 남은 확인

Skare 원본 위치는 `results/benchmark/round_1/skare/qwen36/`이며, 점검 당시 Git 미추적 상태였다. 원본 결과는 이번 문서 커밋에 포함하지 않으므로 별도 공유 전에는 다른 체크아웃에서 볼 수 없다.

- `result.json`의 응답 시간은 69.219746085초, 생성 속도는 38.640686844 tok/s, 원본 판정은 WA 26/41이다. 생성 속도는 서버 `timings.predicted_per_second`이며 Python 전체 응답 시간과 분모가 다르다.
- 응답 후 `nvidia-smi` 관측은 전체 장치 사용량 6461 / 8151 MiB다. 모델 프로세스 VRAM이나 최고 사용량이 아니다.
- 프로세스 VRAM은 null이고, 사유는 matching server PID를 찾지 못했다는 내용이다. WSL은 가능한 원인으로 기록돼 있을 뿐 확정 진단은 아니다. 장치 값을 프로세스 값으로 대체하지 않는다.
- 응답의 `cache_n=0`과 `cached_tokens=0`은 해당 응답의 캐시 카운터다. 요청의 `cache_prompt=false`, 서버 설정, 이전 답변 미전달과 함께 해석하며 전체 실험의 독립성을 단독으로 증명하지 않는다.
- 추출 코드와 저장된 `candidate.py`의 내용 일치를 확인했다. 원본 코드·판정은 유지하며 최소 수정 후 전체 테스트 통과 여부는 미확인이다.
- 워밍업은 호출 완료만 표시하고 저장·측정하지 않는다. 이번 조회로 실제 워밍업 수행 여부를 확인하지 않았다. 요청별 로딩 시간은 API 미제공 사유와 함께 null이며 서버 시작 시간도 측정하지 않았다.

이번 문서 작업에서는 모델·Cloud 호출, 서버 재시작, 채점 재실행을 하지 않았다. 전체 실행 상태와 다음 작업은 [STATE](../STATE.md)를 따른다.
