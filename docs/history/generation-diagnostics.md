# 생성 기록 진단

2026-09-17 저장된 80회 생성 원본(`results/benchmark/`)만으로 수행한 사후 진단이다. **분석과 판단은 AI가 수행했다.** 모델을 다시 실행하지 않았고, 이 기기에는 GGUF와 llama.cpp 런타임이 없어 재생성으로 확인할 수 없다. 따라서 아래의 원인 서술은 저장된 기록에서 읽어낸 관측이며 확정된 인과가 아니다.

집계 대상은 호출에 성공한 78건이다. Motif-3 `skijanje` 두 회차는 제공자 5xx로 실패해 본문 분석에서 제외한다.

[Reasoning 종료 메시지 진단](reasoning-budget-diagnostic.md)은 2026-09-16 단일 사례의 기록이며 이 문서와 구분한다.

## 1. Gemma의 reasoning 퇴행 반복

### 관측

`generation.reasoning_content`를 공백으로 나눈 뒤 12-gram 반복률(중복 등장한 12-gram이 전체에서 차지하는 비중)을 계산했다. 값이 높을수록 같은 구절이 되풀이된다는 뜻이다.

| 문항 | gemma4 round_1 | gemma4 round_2 | qwen36 (두 회차 동일) |
| --- | ---: | ---: | ---: |
| prepisivanje | 92.0% | 92.0% | 11.4% |
| skare | 91.5% | 87.3% | 0.8% |
| pet | 86.1% | 86.1% | 0.7% |
| dzeparac | 81.8% | 85.4% | 2.9% |
| ucionica | 81.5% | 81.5% | 3.2% |
| struktura | 76.3% | 51.7% | 0.2% |
| skijanje | 75.8% | 75.8% | 27.8% |
| cokolada | 52.8% | 60.6% | 2.7% |
| tomahawk | 13.4% | 5.5% | 1.1% |
| tezina | 9.9% | 9.9% | 8.0% |

Gemma는 10문항 중 8문항에서 50% 이상이고 Qwen은 `skijanje` 한 건을 빼면 모두 12% 미만이다. 가장 많이 반복된 12-gram의 등장 횟수는 Gemma `skare` round_1이 **1,085회**, `ucionica` 858회, `pet` 811회다. 예를 들어 `skare`에서는 `` `[10] -> [2, 8] -> [2, 3, 5] -> [2, 3, 2,`` 라는 같은 전개가 반복해서 나타난다.

### 동반 증거

- **예산 소진 고정.** Gemma의 completion 토큰은 20회 중 10회가 54,000~54,800 구간에 몰려 있다. 요청 설정은 `max_tokens=61440`, `reasoning_budget_tokens=53248`이므로, 예산을 다 쓰고 종료 메시지로 끊긴 뒤 짧은 답변이 붙은 형태와 일치한다.
- **출력량 격차.** 평균 completion 토큰이 Gemma 54,454, Qwen 16,570으로 **3.3배**다.
- **종료 사유.** `finish_reason=length`가 Gemma 5회, Qwen 2회다.
- **답변으로 번진 반복.** `tomahawk` round_2는 최종 답변이 **128,353자**에 이르고 `length`로 끊겨 코드가 추출되지 않았다. `ucionica` 32,878자, `skijanje` 26,813자도 같은 양상이다.

### 판단

Gemma의 reasoning 소진은 문항 난이도 때문이 아니라 **퇴행적 반복** 때문이라고 본다. 같은 문항에서 Qwen이 1/10 수준의 토큰으로 끝내고 더 높은 정답률을 낸 것이 대조 근거다.

다만 원인이 모델 자체 특성인지, `reasoning_budget` 설정값인지, Gemma 서버의 `--gpu-layers auto --fit on` 설정인지는 **구분하지 못했다.** 예산을 줄이거나 늘린 재실행으로만 분리할 수 있는데 이 기기에서는 수행할 수 없다.

## 2. temperature 0 결정론으로 인한 회차 중복

### 관측

각 문항의 두 회차 응답(`generation.content`, `generation.reasoning_content`)을 SHA-256으로 대조했다.

| 모델 | 두 회차가 완전히 같은 문항 |
| --- | --- |
| qwen36 | **10 / 10** |
| gemma4 | 5 / 10 |
| luna | 0 / 10 |
| motif3 | 1 / 10 |

### 해석

로컬 두 모델은 `temperature=0`·`cache_prompt=false`로 그리디 디코딩을 쓴다. 같은 입력에 같은 출력이 나오는 것은 설정상 정상 동작이다.

문제는 이것이 평가에 갖는 의미다. **Qwen의 본 실험 20회는 실질적으로 독립 관측 10개와 그 복제 10개**이고, 유효 정답률과 60% 통과선 판정도 결국 10개 관측에 기반한다. 반복 실행이 잡아내려는 실행 간 변동을 Qwen에서는 측정하지 못했다.

Gemma가 5/10만 일치한 것은 배치 커널의 부동소수점 비결합성에서 오는 비결정성으로 보이나, 서버 로그를 남기지 않아 **확정하지 않는다.** 두 로컬 모델의 서버 설정이 다르다는 점(Qwen은 `--gpu-layers all --n-cpu-moe 32` 고정, Gemma는 auto fit)만 기록한다.

### 처리 방침

[요구사항](../project/requirements.md)이 "모델별 정답률의 분모는 항상 20회"로 정해 두었으므로 주 지표는 20회 분모를 유지한다. 고유 응답 기준 보조 수치와 이 한계를 [최종 선정 보고서](../project/model-selection-report.md)에 함께 싣는다.

## 3. 성능과 실패 기록

호출에 성공한 건만 집계했고 n을 함께 표시한다.

| 모델 | n | 응답 시간 평균 | 최대 | 생성 속도 | 출력 토큰 평균 | 예상 비용 합 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen36 | 20 | 427.5s | 1,658s | 39.8 tok/s | 16,570 | 해당 없음 |
| gemma4 | 20 | **1,606.3s** | 1,871s | 34.1 tok/s | 54,454 | 해당 없음 |
| luna | 20 | 254.4s | 988s | null | 24,550 | $0.5929 |
| motif3 | 18 | 245.7s | 501s | null | 18,369 | null |

- Gemma는 문항당 평균 **26분**으로 Qwen의 3.8배다. 생성 속도(tok/s)는 오히려 비슷하므로, 차이는 속도가 아니라 **출력량**에서 온다. 1절의 반복과 같은 원인으로 본다.
- Cloud의 tok/s는 제공자가 서버 생성 구간을 주지 않아 `null`이며 0으로 채우지 않는다.
- Motif-3 비용은 확인한 공개 단가표가 없어 `null`이다. Luna와 비용 축에서 나란히 비교하지 않는다.

### 호출 실패 2건

| 항목 | 오류 |
| --- | --- |
| motif3 skijanje round_1 | `InternalServerError` 502 |
| motif3 skijanje round_2 | `InternalServerError` 504 |

둘 다 제공자 측 5xx이며 **모델 품질 문제가 아니다.** 규정대로 분모 20회에는 남기고 설명 점수에서는 제외한다.

### 코드 미추출 5건

| 항목 | finish_reason | 최종 답변 길이 |
| --- | --- | ---: |
| qwen36 skijanje round_1·round_2 | length | 28,087자 |
| gemma4 skijanje round_1·round_2 | length | 26,813자 |
| gemma4 tomahawk round_2 | length | 128,353자 |

**5건 모두 `length`다.** 출력 한도를 다 써서 코드 블록을 닫지 못한 것이지 코드를 쓰지 않겠다고 한 것이 아니다. `skijanje`(체감 난이도 9)는 로컬 두 모델이 모두 같은 방식으로 실패했다.

## 4. 후보 코드의 결함 유형

원본 `candidate.py` 71개를 훑어 판정과 무관하게 드러난 패턴을 정리한다.

### 함수 호출 누락 (2건, 모두 Gemma)

`struktura/gemma4/round_1`과 `tomahawk/gemma4/round_1`은 마지막 줄이 `solve()`가 아니라 **`solve`** 다. 함수가 호출되지 않아 출력이 전혀 없고 각각 0/130으로 전량 오답이 됐다. 최대 케이스 실행 시간이 0.02~0.04초인 것도 즉시 끝났다는 뜻이다.

### 미완성 스텁 (2건, 모두 Gemma)

`ucionica/gemma4`의 두 회차는 본문에서 세그먼트 트리 풀이를 설명해 놓고 코드는 `pass`로 끝나며, 그 뒤에 `Since the Segment Tree is complex, I will provide a complete, working implementation.`이라는 주석만 남아 있다. 설명한 알고리즘이 구현되지 않았다. 0/91이다.

### 식별자·기호 전사 오류 (Gemma·Luna 양쪽)

- `tezina/luna/round_2`: 41번째 줄이 `un capped_right = CAP // q - 2`로 식별자 중간에 공백이 들어가 `SyntaxError`가 났다. 0/78.
- `struktura/gemma4/round_1` 본문: `$a_i \in \{n-i, n-i+1, n-int+2\}$`로 `n-i+2`가 깨졌다.
- `prepisivanje/gemma4/round_1` 본문: 목록 기호가 `*`가 아니라 `/`로 나온 줄이 있다.

본문 오타는 채점에 영향이 없지만, 코드 안에서 일어나면 그대로 실행 실패가 된다.

### 경계 조건 (1건)

`pet/luna/round_2`는 `if level == len(planes): planes.append(0)`이라 `level`이 `len(planes)`를 건너뛰면 append가 일어나지 않고 `IndexError`가 난다. 10/104.

### 재귀 한도 (2건)

`prepisivanje/gemma4`의 두 회차는 이분 매칭 DFS에 `sys.setrecursionlimit` 설정이 없어 130개 중 120개를 통과한 뒤 `RecursionError`로 끝났다.

### 종합

**전량 오답 4건은 모두 Gemma였고, 알고리즘이 틀려서가 아니라 코드가 실행조차 되지 않아서 생겼다.** 이 중 2건은 괄호 하나, 2건은 구현 자체의 부재다. 실제로 어디까지 회복되는지는 [최소 수정 보조 평가](../operations/evaluation.md)에서 판정했고 결과는 [최종 선정 보고서](../project/model-selection-report.md)에 있다.
