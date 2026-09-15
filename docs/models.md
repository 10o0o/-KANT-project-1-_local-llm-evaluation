# 로컬 모델 후보 조사

[발제 STEP 3](project-brief.md)의 후보 조사 내용을 기록한다. 발제의 후보 조사 항목을 아래 비교표에 함께 기록한다. 미조사 값은 그대로 두고 설치 식별값은 설치 정보 확인 후 작성한다.

## 핵심 비교표

| 항목 | 후보 A | 후보 B |
| --- | --- | --- |
| 모델 이름 / 전체 Ollama 태그 | Qwen3.6-35B-A3B / `qwen36-35b-lowvram:latest` | Gemma 4 26B A4B IT / `gemma4:26b-a4b-it-q4_K_M` |
| 공식 Model Card 링크 | [링크](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | [Google 공식 모델 카드](https://ai.google.dev/gemma/docs/core/model_card_4) |
| License 이름·원문 링크 | [Apache license 2.0](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/LICENSE) | [Apache 2.0](https://ai.google.dev/gemma/apache_2) |
| 파라미터 수 | 35B | Ollama 조회 25.8B; 공식 MoE 표 25.2B / 활성 3.8B, 비전 인코더 약 550M 별도 표기 |
| 모델 파일 크기 | 21.2GB | [18GB](https://ollama.com/library/gemma4:26b-a4b-it-q4_K_M) |
| 문서상 최대 Context (토큰) | 262,144 | 256K; Ollama 조회 262,144 |
| 양자화 형식 | Q4_K_M | Q4_K_M |
| 모델 ID/digest | c1f47f017694 | `5571076f3d70` (전체 digest는 아래) |
| Architecture | qwen35moe | gemma4 / Mixture-of-Experts (MoE) |
| 지원 언어 | 지원 언어 목록 미명시 | 공식 카드: 35개 이상 언어 지원, 140개 이상 언어 사전학습 |
| 공개 Benchmark·출처 | LiveCodeBench v6, AIME26 등 — [공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B#benchmark-results) | LiveCodeBench v6 77.1%, AIME 2026 88.3%, Codeforces ELO 1718 — [공식 카드](https://ai.google.dev/gemma/docs/core/model_card_4#benchmark_results), 원본 IT 평가이며 로컬 Q4 실측 아님 |
| Ollama·GGUF와 원본 모델의 대응 관계 | `qwen3.6:35b-a3b-q4_K_M`의 동일 가중치를 사용하는 설정 변경본 (`num_gpu 12`, `num_ctx 4096`) | Gemma 4 26B A4B instruction-tuned 모델의 Ollama Q4_K_M 배포 — [태그 출처](https://ollama.com/library/gemma4:26b-a4b-it-q4_K_M) |
| 후보 선정 이유 | 로컬 LLM관련 reddit 커뮤니티 반응을 조사한 결과 괜찮은 후보가 qwen3.6이라고 판단함 (기존 공동 선정 이유 원문은 제외 이력에 보존) | HyperCLOVA를 현재 구성의 성능 미달로 제외하고, 이미 Ollama에 설치된 Gemma를 대체 후보로 선택함. 실제 적합성은 이후 직접 평가 |

## 후보 A 실행 설정 확인

원본 설정으로 구동이 어려워 아래 설정으로 변경한 뒤 구동했다. Ollama 조회에서 `qwen36-35b-lowvram:latest` 등록과 설정을 확인했다.

```text
FROM qwen3.6:35b-a3b-q4_K_M
PARAMETER num_gpu 12
PARAMETER num_ctx 4096
```

- 실행 모델: `qwen36-35b-lowvram:latest`, 짧은 ID `c1f47f017694`.
- 전체 digest: `c1f47f01769450c584d5779ce1ef0bfc34799937782e0168694ec1a4125b63a1`.
- 기반 등록 모델: `qwen3.6:35b-a3b-q4_K_M`, ID `07d35212591f`. 같은 가중치와 Q4_K_M 양자화를 사용하며 별도 재양자화가 아니다.
- GPU 레이어 설정은 12, 실행 Context 설정은 4096이다. 표의 문서상 최대 Context 262,144와 구분한다. 호출 시 옵션으로 덮어쓰면 실제 사용한 설정을 따로 기록한다.
- [사용자 Modelfile](/home/jake/workspace/local-llm/configs/ollama/qwen3.6-35b-a3b-q4_K_M/Modelfile)과 [기존 실행 안내](/home/jake/workspace/local-llm/configs/ollama/qwen3.6-35b-a3b-q4_K_M/README.md)는 현재 PC의 외부 참고 위치다. 제출 시 재현에 필요한 설정을 저장소 안에 남긴다.
- 기존 실행 안내에는 이전 측정값 약 6.04 tok/s·GPU 메모리 6,835 MiB가 있다. 이번 조회에서는 추론을 재실행하지 않았고 `ollama ps`는 비어 있었다. 이 수치를 본 실험 결과로 집계하지 않는다.

## 후보 B Gemma 설치 확인

공식 출처와 AI의 읽기 전용 조회 결과를 참고해 조사표를 정리했다. 이후 CLI·Python 기본 호출을 진행하고 결과를 `results/`에 저장했다. 이 절은 당시 기본 호출 이력이며 이후 코딩테스트 평가는 [STATE](../STATE.md)와 결과 기록에서 확인한다.

- 전체 digest: `5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251`.
- 기본 호출에서 Context 4096과 응답 저장·재읽기를 확인했다. 당시 CLI의 CPU/GPU 적재 비율은 73%/27%였다. 자세한 진행 근거는 [STATE](../STATE.md)에 기록했다.
- 이후 llama.cpp 전환과 현재 실행·평가 상태는 [STATE](../STATE.md)를 따른다. 위 Ollama 식별값과 연결 결과는 당시 이력으로 보존하며 새 GGUF와 같은 파일이라고 간주하지 않는다.

## 제외 이력: HyperCLOVA

2026-09-14 진단을 종료하고 후보에서 제외했다. 현재 Q4_K_M·NAVER llama.cpp 구성에서 단순 질문의 주제와 두 문장 지시를 반복적으로 따르지 못해 성능이 요구 수준에 미달한다고 판단했다. 원본 모델 전체의 성능 평가나 본 실험 40회의 최종 결과는 아니다. 상세 경과는 [Notion 일지](https://app.notion.com/p/3dbde5bf907481bab6aed707634ae1e0)에 보존한다.

### 교체 전 조사표 원문

| 항목 | 후보 A | 후보 B |
| --- | --- | --- |
| 모델 이름 / 전체 Ollama 태그 | Qwen3.6-35B-A3B / `qwen36-35b-lowvram:latest` | HyperCLOVAX-SEED-Think-14B-GGUF:Q4_K_M |
| 공식 Model Card 링크 | [링크](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | [링크](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-14B) |
| License 이름·원문 링크 | [Apache license 2.0](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/LICENSE) | [hyperclovax-seed](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-14B/blob/main/LICENSE) |
| 파라미터 수 | 35B | 15B |
| 모델 파일 크기 | 21.2GB | 8.92GB |
| 문서상 최대 Context (토큰) | 262,144 | 32,000 |
| 양자화 형식 | Q4_K_M | Q4_K_M |
| 모델 ID/digest | c1f47f017694 | ee0e0d9ce93e |
| Architecture | qwen35moe | hcx-seed-think |
| 지원 언어 | 지원 언어 목록 미명시 | 한국어·영어 평가 결과 제공, 전체 지원 언어 목록 미명시 |
| 공개 Benchmark·출처 | LiveCodeBench v6, AIME26 등 — [공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B#benchmark-results) | HumanEval, MBPP, MATH500 등 — [공식 모델 카드](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-14B#benchmarks) |
| Ollama·GGUF와 원본 모델의 대응 관계 | `qwen3.6:35b-a3b-q4_K_M`의 동일 가중치를 사용하는 설정 변경본 (`num_gpu 12`, `num_ctx 4096`) | 원본 모델의 Q4_K_M 양자화 |
| 후보 선정 이유 | 로컬 LLM관련 reddit 커뮤니티 반응을 조사한 결과 괜찮은 후보가 qwen3.6이고, 최근 국가대표 AI 선발 모델 리스트에서 로컬에서 구동해볼만한 모델이 HyperCLOVAX로 선정했다 |  |

### 제외 전 실행 도구 예외와 점검 이력

HyperCLOVA만 NAVER `llama.cpp` 포크로 진행하기로 했다. 이는 [사용자 선택 실행 도구 예외](guide.md#현재-후보와-hyperclova-제외-이력)이며 과제 측의 승인 여부는 확인되지 않았다. 위 조사값은 보존하며 다운로드 식별자와 실제 실행 도구를 구분한다.

- 다운로드한 전체 Ollama 태그: `hf.co/naver-ellm/HyperCLOVAX-SEED-Think-14B-GGUF:Q4_K_M`. 교체 전 표의 `ee0e0d9ce93e`는 Ollama 등록 ID이며 실행 도구 버전이 아니다.
- 실행 도구: [NAVER 포크](https://github.com/NAVER-Cloud-HyperCLOVA-X/llama.cpp), 조회한 커밋 `e586ccd5`. [GGUF 모델 카드](https://huggingface.co/naver-ellm/HyperCLOVAX-SEED-Think-14B-GGUF) 본문에도 이 포크 사용을 안내한다.
- [설정·실행 안내](/home/jake/workspace/local-llm/configs/llama-cpp/hyperclovax-seed-think-14b-q4_K_M/README.md), 소스·빌드 위치 `/home/jake/workspace/local-llm/runtimes/hyperclovax-llama.cpp`. CUDA 빌드 설정과 `build/bin/llama-cli`, `build/bin/llama-server` 파일 존재를 확인했다. 파일 존재는 정상 추론 성공 근거가 아니다.
- 기존 Ollama GGUF blob을 재다운로드 없이 참조하는 구성이다. 조회한 가중치 경로는 `/usr/share/ollama/.ollama/models/blobs/sha256-34189c1048e57b9b0025058114185ce4dc37d045596666b67e377ef1f08398c0`이다. Ollama 모델 삭제로 파일 참조가 끊길 수 있다. 외부 경로는 현재 PC의 참고 위치이며 제출 시 재현 방법을 남긴다.
- 기존 안내의 GPU 레이어 `24`, Context `4096`, 서버 `127.0.0.1:8080`은 시작 설정이다. 당시 실제 설정과 최적값은 미확인이다.
- 당시 실행 경험: 처음 Ollama에서 오류가 나 별도 환경을 구성했고, 응답을 받았으나 출력이 이상하며 VRAM이 약 600MB로 보였다. 최초 오류 시점·당시 명령·오류·응답 원문과 VRAM 측정 도구·시점·정확한 단위는 미확보다. CPU 실행이나 GPU 미사용으로 단정하지 않는다.
- 이후 CLI·Python 및 GPU 레이어 요청 24·0에서 동일 질문 이탈을 확인했다. 현재는 **진단 종료·후보 제외** 상태이며 모델 파일과 실습 코드는 보존한다. 원인 자체는 확정하지 않았으며 연결 확인을 본 실험으로 집계하지 않는다.
