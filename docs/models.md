# 로컬 모델 후보 조사

[발제 STEP 3](project-brief.md)의 후보 조사 내용을 기록한다. 발제의 후보 조사 항목을 아래 비교표에 함께 기록한다. 미조사 값은 그대로 두고 설치 식별값은 설치 정보 확인 후 작성한다.

## 핵심 비교표

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

## 후보 A 실행 설정 확인

사용자는 원본 설정으로 구동이 어려워 아래 설정으로 변경한 뒤 구동했다고 설명했다. Ollama 조회에서 `qwen36-35b-lowvram:latest` 등록과 설정을 확인했다.

```text
FROM qwen3.6:35b-a3b-q4_K_M
PARAMETER num_gpu 12
PARAMETER num_ctx 4096
```

- 실행 모델: `qwen36-35b-lowvram:latest`, 짧은 ID `c1f47f017694`.
- 전체 digest: `c1f47f01769450c584d5779ce1ef0bfc34799937782e0168694ec1a4125b63a1`.
- 기반 등록 모델: `qwen3.6:35b-a3b-q4_K_M`, ID `07d35212591f`. 같은 가중치와 Q4_K_M 양자화를 사용하며 별도 재양자화가 아니다.
- GPU 레이어 설정은 12, 실행 Context 설정은 4096이다. 표의 문서상 최대 Context 262,144와 구분한다. 호출 시 옵션으로 덮어쓰면 실제 사용한 설정을 따로 기록한다.
- [사용자 Modelfile](/home/jake/workspace/local-llm/configs/ollama/qwen3.6-35b-a3b-q4_K_M/Modelfile)과 [기존 실행 안내](/home/jake/workspace/local-llm/configs/ollama/qwen3.6-35b-a3b-q4_K_M/README.md)는 현재 PC의 외부 참고 위치다. 제출 시 사용자는 재현에 필요한 설정을 저장소 안에 남긴다.
- 기존 실행 안내에는 사용자 이전 측정값 약 6.04 tok/s·GPU 메모리 6,835 MiB가 있다. 이번 조회에서는 추론을 재실행하지 않았고 `ollama ps`는 비어 있었다. 이 수치를 본 실험 결과로 집계하지 않는다.

파일 크기는 기존 사용자 기록을 보존했다. 이번 `/api/tags`의 등록 모델 크기는 23,938,333,343바이트(약 23.94 GB / 22.29 GiB)로, 표의 21.2GB와 출처·단위 대조가 남아 있다.
