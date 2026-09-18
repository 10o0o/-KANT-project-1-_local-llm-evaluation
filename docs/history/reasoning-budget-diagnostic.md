# Reasoning 종료 메시지 진단

2026-09-16 Tomahawk의 답변 전환을 진단했다. 첨부 해석문에 인용된 로그, 직접 실행·확인한 내용, AI의 현재 코드·결과 재읽기를 구분해 기록한다. 서버 원본 로그 전체는 저장소에서 대조하지 못했다.

## 이전 실패와 판단

공유한 해석문에는 다음 로그가 인용돼 있다.

```text
activated, budget=2048 tokens
budget exhausted, forcing end sequence
forced sequence complete, done
```

이 인용은 해당 요청에서 reasoning budget 2048이 활성화되고 소진 후 강제 종료가 수행됐다는 근거다. 해석문은 종료 후 content가 추론의 연속처럼 시작하고 completion 8192, `length`, `NO_CODE`로 끝났다고 보고했다. 해당 이전 진단의 원본 응답·전체 로그는 이번 점검에서 직접 대조하지 못했다. 모든 요청의 예산 동작으로 일반화하지 않는다.

종료 메시지 없이 종료 태그만 강제한 것이 답변 전환 실패의 유력 원인이라고 판단했다. 다만 이 자료만으로 VRAM·Context·출력 한도·모델 동작 등 다른 요인을 모두 배제하거나 원인이 확정됐다고 보지는 않는다.

## 요청 변경과 소스 근거

공통 `chat()` 요청에 `reasoning_budget_message`를 추가했다. 현재 작업 트리에서는 두 모델과 워밍업·benchmark에 공통 적용되며, 서버 셸 기본값이 아닌 요청 본문 설정이다. 메시지 본문은 다음과 같다.

```text
Considering the limited time by the user, I have to give the solution based on the thinking directly now.
```

메시지에 `</think>`를 직접 넣지 않는다. 로컬에서 확인한 llama.cpp 커밋 `4c9233c034fc450dcf34c7c0988aebe6da5cdf1a`의 [요청 처리](https://github.com/ggml-org/llama.cpp/blob/4c9233c034fc450dcf34c7c0988aebe6da5cdf1a/tools/server/server-common.cpp)와 [서버 스키마](https://github.com/ggml-org/llama.cpp/blob/4c9233c034fc450dcf34c7c0988aebe6da5cdf1a/tools/server/server-schema.cpp)는 이 필드를 읽고 메시지 토큰을 reasoning 종료 태그 앞에 붙인다. [예산 상태 전이](https://github.com/ggml-org/llama.cpp/blob/4c9233c034fc450dcf34c7c0988aebe6da5cdf1a/common/reasoning-budget.cpp)도 위 로그와 대응한다.

공통 적용 사실과 각 모델에서의 효과는 다르다. Gemma에서도 동일한 개선이 확인됐다거나 공정성이 검증됐다고 판단하지 않는다. 이번 문서 커밋에는 이미 수정한 요청 코드·서버 셸을 포함하지 않는다. 따라서 이 절의 적용 상태는 문서 작성 당시 작업 트리 기준이다.

## 추가 후 재진단

종료 메시지 추가 후 실행한 진단임을 대화에서 확인했다. AI가 현재 저장 파일을 다시 읽어 다음 내용을 대조했다.

| 항목 | 확인값 |
| --- | --- |
| Run ID | `20260916_124351_312419` |
| 모델·문제 | Qwen / Tomahawk |
| 최초 확인 위치 | `results/benchmark/round_1/tomahawk/qwen36/` |
| 문서 검증 중 확인한 보관 위치 | `results/pilot/reasoning_block/tomahawk/qwen36/` |
| 종료·completion 토큰 | `stop` / 3703 |
| 최종 답변·코드 | 접근법·설명·Python 코드 생성 |
| 원본 채점 | `RE` |
| 집계 | 진단 실행, 본 실험 40회에서 제외 |

메시지 추가 후 최종 답변 형식으로 전환된 사례를 확인했다. 정답 성공은 아니며, 동일 조건의 통제 비교와 이번 요청의 budget 소진 원본 로그가 함께 보존되지 않아 인과를 단독으로 확정하지 않는다. 기존 `RE`나 생성 코드는 변경하지 않는다.

현재 결과의 `generation_config`에는 temperature 0, max_tokens 8192, reasoning_budget_tokens 2048, cache_prompt false가 있으나 **reasoning_budget_message는 저장되지 않는다**. 적용 시점은 직접 실행한 확인에 근거하며 JSON 자체가 종료 메시지를 증명하지는 못한다. 성공·실패 기록에 이 필드를 보존하는 코드 보완은 별도 후속 작업이다.

## 본 실험과 분리할 사항

최초 확인 경로와 `experiment.type`은 benchmark였지만 위 run ID는 진단이다. 문서 검증 도중 `results/pilot/reasoning_block/tomahawk/qwen36/`로 이동된 것을 확인했다. AI는 이동을 수행하지 않았고 보관된 원본 내용은 최초 확인 파일과 일치한다. 현재 보관된 진단 원본은 Git 미추적 상태이며 이번 문서 커밋에는 포함하지 않는다. 별도 공유 전에는 다른 체크아웃에 원본이 없다. JSON의 benchmark 유형과 무관하게 [결과 분류](../../results/README.md)에 따라 본 실험 품질·성능 평균과 40회 집계에서 제외한다.

실행기는 완료된 결과를 건너뛰므로 이 진단을 원래 benchmark 경로에 다시 두면 정식 Round 1 요청이 건너뛰어진다. 이번 점검에서 진단의 경로 분리를 확인했다. 이후 요청 설정 기록은 보완됐고 실험 조건은 Context 65,536·출력 61,440·reasoning 53,248로 동결한 뒤 본 실험 80회를 생성했다.

현재 Qwen 셸의 `-lv 4`는 진단 설정이다. 이번 문서 작업에서는 결과 삭제·이동·JSON 수정, 모델 호출·재채점·서버 재시작, 로그 레벨 복귀를 수행하지 않았다. 아래 문장은 작성 당시 서술이며, 조건 동결과 본 실험 완주는 이후 2026-09-17에 이뤄졌다. 이전 12:22 결과 관측은 [결정 이력](decision-log.md)의 과거 기록으로 구분한다.

## 후속 반영: 2026-09-16 실행 제한·경로 통합

위 내용은 진단 당시 기록이다. 이후 공통 종료 메시지를 상수로 분리하고 새 로컬 성공·실패 결과의 `generation_config.reasoning_budget_message`에 저장하도록 보완했다. 과거 진단 JSON은 수정하지 않았다. 현재 본 실험 설정과 경로는 [README](../../README.md)를 따른다. 기존 결과를 옮겨 새 조건의 완료 기록으로 재사용하지 않는다.
