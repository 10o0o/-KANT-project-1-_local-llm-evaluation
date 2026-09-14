# 로컬 모델 후보 조사

[발제 STEP 3](project-brief.md)의 후보 조사 내용을 기록한다. 아래는 핵심 비교표이며, 본문의 확인 사항은 필요한 내용을 짧게 덧붙인다. 미조사 값은 그대로 두고 설치 식별값은 설치 정보 확인 후 작성한다.

## 핵심 비교표

| 항목 | 후보 A | 후보 B |
| --- | --- | --- |
| 모델 이름 / 전체 Ollama 태그 | qwen3.6:35b-a3b-q4_K_M | HyperCLOVAX-SEED-Think-14B-GGUF:Q4_K_M |
| 공식 Model Card 링크 | [링크](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | [링크](https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-14B) |
| License 이름·원문 링크 | Apache license 2.0 | hyperclovax-seed |
| 파라미터 수 | 35B | 15B |
| 모델 파일 크기 | 21.2GB | 8.92GB |
| 문서상 최대 Context (토큰) | 262,144 | 32,000 |
| 양자화 형식 | Q4_K_M | Q4_K_M |
| 모델 ID / digest — 설치 정보 확인 후 작성 | 미조사 | 미조사 |
| 후보 선정 이유 | 로컬 LLM관련 reddit 커뮤니티 반응을 조사한 결과 괜찮은 후보가 qwen3.6이고, 최근 국가대표 AI 선발 모델 리스트에서 로컬에서 구동해볼만한 모델이 HyperCLOVAX로 선정했다 |

## STEP 3 보충 메모

Architecture·지원 언어·공개 Benchmark와 출처·Ollama 모델과 원본의 대응 관계는 발제 본문의 확인 사항이다. 이미 표에 적은 내용은 반복해서 작성하지 않는다. 공개 Benchmark와 직접 실험한 성능은 구분한다.

- **후보 A:** 미조사.
- **후보 B:** 미조사.

실제 Context·VRAM·생성 설정·실행 실패는 [STEP 4·6](guide.md)의 실제 실행 기록에 남긴다. 지금 별도 측정표를 채울 필요는 없으며, 문서상 최대 Context와 실제 실행 Context, 파일 크기와 실행 중 메모리는 구분한다.

서로 다른 로컬 후보 두 개를 조사한다. 같은 모델의 양자화 버전 두 개만으로 이 요건을 대신하지 않는다. 최종 선정은 실제 실험과 평가 이후에 한다.
