# Cloud 비교 실행

모든 `uv run llm-eval` 명령은 저장소 루트 `/home/jake/workspace/projects/kant/local-llm-evaluation`에서 실행한다. Cloud `--model`은 필수이며 `luna` 또는 `motif3`를 선택한다. `--round`는 생략하면 1이며, 2를 선택하면 같은 입력·설정의 독립 회차를 새로 저장한다.

## 범위와 발제 대응

[Notion 발제 STEP 5·7](https://app.notion.com/p/3ddde5bf9074809787d7f6a5a5a263e7)과 [수행 평가표](https://app.notion.com/p/3ddde5bf9074801ba56fd9356c80e820)의 원래 기준은 Cloud 1개·공통 5문항·각 1회다. 발제 원문은 변경하지 않는다. 이번 사용자 수행 범위는 **기존 10문항 전체를 두 회차 독립 실행하는 10문항×2회=20회**다. 별도의 5문항 추가 실행이나 5문항 분모를 만들지 않는다. 일부 로컬 결과를 확인한 뒤 전체 10문항 적용을 결정한 경과를 밝히며 결과를 보기 전 5개를 선정했다고 소급하지 않는다.

Cloud 비교 대상은 **Luna와 Motif-3 두 제공자**다. Motif-3는 Luna 실행기를 확장해 추가한 두 번째 Cloud 대상이며, 발제 원문과 기존 사용자 수행 범위 어디에도 없던 추가 확장이다. 두 모델은 같은 10문항·같은 프롬프트·같은 Judge를 쓰지만 서로 다른 제공자·API 계열·생성 설정을 사용하므로 **각각 20회의 독립 분모**를 가지며 하나의 Cloud 분모로 합치지 않는다. Motif-3의 실제 호출은 이 문서 작성 시점에 수행하지 않았고 결과·정답률·비용은 미확인이다.

로컬 20회와 Cloud 모델당 20회는 같은 10문항을 두 번씩 독립 실행한다. 제공자와 생성 설정은 다르므로 동일 조건으로 표시하지 않으며, 문제 목록·반복 수·독립성만 공통 비교 축으로 둔다. 로컬과 Cloud 모두 두 회차 중 좋은 결과만 고르지 않는다. 실패·NO_CODE도 Cloud 유효 정답률의 분모에 포함하고 미실행은 별도로 표시한다. 20회 실행 범위를 모두 확인한 뒤 최종 Cloud 유효 정답률은 유효 정답 수/20, 일반 AC 비율은 AC 수/20으로 계산한다. 미실행분은 실패나 NO_CODE로 세지 않고 별도로 표시한다. 유효 정답은 AC이면서 적용 시간 제한 미만인 결과다. 로컬의 12/20(60%) 통과선을 Cloud에 적용하지 않으며 Cloud 결과는 최종 로컬 후보 선정에서 제외한다. 호출 성공 수/실제 시도 수도 따로 표시하며, 20회 완료 전에는 최종 비율을 확정하지 않고 실제 시도 수와 미실행을 구분한다. 설명·시간·토큰·비용 평균은 해당 근거가 있는 응답의 n을 각각 표시한다. 설명 채점·비교 집계·최종 선정은 후속 작업이다.

확인한 중단 기록에는 Luna Round 1의 10건이 포함되며 호출은 성공했지만, 이는 Cloud 20회 완료나 최종 정답률 산출 근거가 아니다. Round 2를 포함한 전체 계획은 로컬 40회와 Cloud 20회의 총 60회로 유지한다. 현재 저장소는 `/home/jake/workspace/projects/kant/local-llm-evaluation`이며, 이번 문서 유지보수에서는 Cloud 호출이나 Judge를 실행하지 않았다.

## 확정한 Cloud 조건

초기 Cloud 구현 때 다른 저장소의 `project1-python-start/02_luna_chat.py`를 참고했다. Motif-3는 제공자가 배포한 연동 예제의 `base_url`·모델 ID·최소 요청 형태를 그대로 따랐다. 외부 예제 원본은 수정하지 않았다.

두 모델의 공통 조건은 다음과 같다.

| 항목 | 값 |
| --- | --- |
| Timeout / 자동 재시도 | 3600초 / 0회 |
| temperature | 보내지 않음, 서비스 기본값 적용 |
| 입력 | 로컬과 동일한 실행 제한·문제문을 포함한 단일 user prompt, 이전 답변·정답·채점 데이터 미전달 |
| 잠금 | 저장소별 Cloud 전용 잠금 하나를 공유하므로 두 Cloud 모델을 동시에 실행할 수 없다 |

모델별 조건은 API 계열이 달라 다음과 같이 갈린다. 두 열을 같은 조건으로 표시하지 않는다.

| 항목 | `--model luna` | `--model motif3` |
| --- | --- | --- |
| API 계열 | OpenAI Responses API | OpenAI 호환 Chat Completions |
| 요청 모델 | gpt-5.6-luna | motif/motif-3 |
| Endpoint | `https://api.openai.com/v1` | `https://api-cbt.morphfactory.io/v1` |
| 환경 변수 | `openai_secret_key` | `morph_secret_key` |
| Reasoning | effort=max | 제공자 파라미터 없음, 보내지 않음 |
| 출력 한도 | max_output_tokens 128000, 추론과 최종 답변 합계 | 보내지 않음, 서비스 기본값 적용 |
| Tools / tool_choice | 빈 목록 / none | 보내지 않음 |
| store / service_tier | false / default | 제공자 필드 없음 |
| 완료 판정 | 응답의 `status` | `finish_reason`을 `stop`→completed, `length`→incomplete로 대응 |
| 결과 경로 | `results/benchmark/<문제>/luna/` | `results/benchmark/<문제>/motif3/` |

Motif-3에는 검증한 예제가 보내는 `model`과 `messages`만 전송한다. Luna의 reasoning·출력 한도·tool 설정을 Motif-3에 옮겨 적지 않으며, 두 모델의 토큰 예산을 같은 조건으로 표시하지 않는다.

[Luna 공식 문서](https://developers.openai.com/api/docs/models/gpt-5.6-luna)와 [Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)를 확인했다. Cloud는 로컬 Context 65536·출력 61440·reasoning 53248와 동일 예산이 아니다. Cloud의 effort=max를 로컬 reasoning 토큰 수로 환산하지 않는다. llama.cpp 전용 종료 메시지·cache_prompt·Context 설정은 보내지 않는다. 캐시는 서비스 동작을 따르며 응답의 캐시 읽기·쓰기 토큰을 기록한다. `store=False`를 캐시 비활성화나 모든 서비스 로그 미보존으로 해석하지 않는다.

## 실행

생성 실행기는 응답·지표·후보 코드까지만 저장한다. Cloud는 로컬 생성·워밍업·큐·서버와 실행 순서에 관계없이 병행할 수 있다. Cloud 워밍업은 없고 모델·생성 설정은 코드에 고정한다.

이 문서에서는 Cloud 호출이나 비밀 파일을 저장소에 복사하지 않는다. 아래 `.env` 상대 경로 명령은 최종 통합 저장소 루트에서 실행할 때만 사용한다.

선택한 모델의 환경 변수(Luna는 `openai_secret_key`, Motif-3는 `morph_secret_key`)가 실행 환경에 있으면 최종 통합 저장소 루트에서 다음 명령을 사용한다. 회차를 생략하면 기존 기본값인 Round 1을 실행한다.

Cloud 생성은 `logs/.cloud-workload.lock`을 사용한다. 다른 Cloud 생성이나 채점이 실행 중이면 요청·회차·모델이 달라도 시작을 차단한다. 두 Cloud 모델은 순차로 실행한다. 로컬 생성·워밍업·큐는 기존 `logs/.workload.lock`을 유지한다. 모델 서버는 잠금을 직접 획득하지 않으며 프로세스 검사 대상이다. 일괄 채점과 단일 후보 실행은 로컬→Cloud 순서로 두 잠금을 획득하고, 전체 생성 완료·서버 종료 후 실행한다.

```bash
uv run llm-eval generate cloud --model luna   --problems all --round 1
uv run llm-eval generate cloud --model luna   --problems all --round 2
uv run llm-eval generate cloud --model motif3 --problems all --round 1
uv run llm-eval generate cloud --model motif3 --problems all --round 2
```

기존 예제 저장소의 `.env`를 사용하려면 파일을 복사하지 않고 실행할 때만 로드한다. 예제 저장소가 현재 저장소의 형제 디렉터리인 경우다.

```bash
uv run --env-file ../project1-python-start/.env llm-eval generate cloud --model luna --problems all --round 1
uv run --env-file ../project1-python-start/.env llm-eval generate cloud --model luna --problems all --round 2
```

`--round`를 생략하면 표준 CLI의 기본값인 Round 1을 실행한다. Round 2는 Round 1이 없어도 실행할 수 있다. `--model`에는 기본값이 없다. 유료 호출의 대상을 추론하지 않기 위해 매번 명시한다.

선택 실행은 `--problems`에 기존 문제 ID를 쉼표로 나열한다. 이번 명령에서 선택한 ID 목록을 invocation에 남기며 회차당 10회와 전체 계획 20회를 구분한다. 중복 ID는 거부한다. 키가 없으면 요청 전에 중단한다. 키 값은 문서·코드·결과에 저장하지 않는다.

## 결과와 실패 보존

신규 기록은 experiment.round에 선택 회차, planned_attempts에 전체 계획 20을 저장한다. 기존 Round 1의 planned_attempts=10과 저장 파일은 수정하지 않으며 같은 요청이면 SKIP한다.

`results/benchmark/<문제 이름>/<luna 또는 motif3>/round_<회차>/` 아래에 API 원본 `response.json`, 코드가 있으면 `candidate.py`, 정리된 `result.json`을 저장한다. Cloud 모델별로 round 1·2 각각 10문항을 저장해 모델당 20회로 관리한다. 두 모델의 결과 트리는 분리되어 있어 서로 덮어쓰거나 건너뛰지 않는다. 채점은 전체 생성 완료와 로컬 모델 서버 종료 후 별도로 실행한다. 요청 모델과 반환 모델·response ID·전체 입력·실제 전송 설정·usage·호출 상태·API 상태를 저장하며 `judge=null`을 유지한다.

- `call.status=success`는 completed 또는 incomplete 응답을 받았다는 뜻이다. 정답이나 생성 완료를 뜻하지 않는다. API 완료 여부는 `generation.status`와 `incomplete_details`로 확인한다.
- Motif-3 기록의 `generation.status`는 응답 필드가 아니라 `finish_reason`에서 옮긴 값이며 원본 `finish_reason`도 함께 저장한다. `choices`가 비었거나 `stop`·`length`가 아닌 종료 사유는 비정상 상태로 저장한 뒤 중단한다. 저장한 `usage`는 제공자 원본 그대로이며 필드 이름 대응은 지표 계산에서만 적용한다.
- incomplete도 코드를 추출해 저장한다. 후속 일괄 채점에서 코드가 있으면 실행하고 없으면 NO_CODE다. 거절 원문은 response.json에 보존한다. failed 등 비정상 API 상태는 저장 후 중단한다.
- API 예외·timeout은 안전한 오류 유형·HTTP 상태와 실패까지의 시간만 기록한 뒤 중단한다. 헤더·전체 예외 문자열을 출력하거나 저장하지 않는다.
- 입력·전송 설정이 같은 완료된 성공·실패 시도는 재실행 시 건너뛴다. 기존 기록과 입력·설정이 다르면 재호출하지 않고 중단한다. 원본 실패를 성공으로 교체하지 않는다. 불완전한 폴더나 생성 후처리 오류는 자동 재호출 없이 중단한다. 기존 채점 오류로 미완료인 폴더도 자동 복구하지 않는다. `record_complete`는 파일 처리 완료 표시로 모델의 정답 판정과 다르다.
- 파일·기록을 삭제해서 재시도하지 않는다. 추가 실험·재시도는 별도 원본 보존과 집계 분리가 필요하며 이번 실행기는 자동 재시도를 지원하지 않는다.

네트워크 포함 전체 응답 시간은 API 호출 직전부터 반환 직후까지이며 저장·채점 시간은 제외한다. Cloud VRAM·로딩 시간·서버 generation tok/s는 API 미제공 사유와 함께 null이다. 출력 토큰÷전체 응답 시간을 로컬 생성 속도와 같은 지표로 만들지 않는다. 내부 reasoning 전문은 요청하거나 만들어 기록하지 않고 제공된 토큰 수만 보존한다.

## 생성 후 채점

로컬·Cloud 생성과 모델 서버를 모두 종료한 뒤 저장소 루트에서 실행한다.

```bash
uv run llm-eval judge batch --problems all --models all --rounds all
```

Cloud만 선택하려면 `--models luna,motif3 --rounds 1,2`를 사용한다. 한 제공자만 채점하려면 `--models motif3`처럼 하나만 적는다. 모델 API나 인증키 없이 저장된 후보를 순차 실행한다. 각 실행은 새 `results/judging/<세션 ID>/`에 저장하며 기존 생성 결과는 변경하지 않는다. [채점 세션과 집계 기준](../../results/README.md#일괄-채점-세션)을 따른다. 단일 후보 검증은 `uv run llm-eval judge candidate --code <path> --problem <id>`를 사용한다. 이전 script aliases는 제거됐으며, 이름 대응표는 [architecture](../architecture.md)에 역사적 기록으로 남아 있다.

Judge는 테스트마다 경과 시간과 stdout·stderr 합산 출력 10 MiB(10,485,760 bytes)를 적용한다. 시간 초과와 출력 초과가 함께 관측되면 먼저 발생한 자원을 `TLE` 또는 `OLE`로 기록하며, 세션·처리 인프라 예외는 `JUDGE_ERROR`로 남긴다. `manifest.json`의 `judge_policy`에는 `version`, `per_test_output_limit_bytes`, `output_limit_scope`, `resource_verdict_precedence`를 저장한다. 이 정책 설명은 실제 채점 실행 완료를 뜻하지 않는다.

## 비용

비용 추정은 공개 단가표를 확인한 모델에만 적용한다. **Motif-3는 확인한 공개 단가표가 없으므로 예상 비용을 계산하지 않고 `estimated_usd=null`과 사유를 기록한다.** 단가를 추정해 넣으면 Luna 비교표까지 근거를 잃으므로 임의 값을 채우지 않는다. Motif-3 비용을 비교에 넣으려면 제공자의 공식 단가와 확인일을 먼저 문서에 남기고 코드의 단가표를 갱신한다.

아래는 Luna 단가다. 2026-09-16 [공식 단가](https://developers.openai.com/api/docs/models/gpt-5.6-luna)를 재확인했다. 표준 처리·일반 길이의 텍스트 입력을 대상으로 100만 토큰당 USD 입력 0.20, 캐시 읽기 0.02, 캐시 쓰기 0.25(일반 입력의 1.25배), 출력 1.20을 사용한다.

`일반 입력 = input_tokens - cached_tokens - cache_write_tokens`로 구분해 각 단가를 적용한다. reasoning 토큰은 output_tokens에 포함되므로 다시 더하지 않는다. 단가·출처·확인일·비용 종류를 결과에 함께 남긴다.

사용량·캐시 구분이 누락되거나 비정상인 경우, 응답 모델/처리 등급이 확인한 단가와 다른 경우, 입력이 272000토큰을 초과해 장문 단가가 필요한 경우에는 예상 비용을 null과 사유로 기록한다. 0토큰과 미측정은 구분한다. 단가 변경 시 실행 전 표를 다시 확인하고 코드를 갱신해야 한다. 실제 청구액은 [API 사용량](https://platform.openai.com/usage)과 별도로 대조하며 예상 비용을 실제 청구라고 표시하지 않는다.

## 검증과 남은 작업

AI의 모의 검증 결과를 참고했다. 이번 문서·통합 준비 작업에서는 실제 Cloud 호출·로컬 모델 호출·생성 코드 채점을 하지 않았다. 확인한 35건의 중단 기록과 기존 프롬프트의 Cloud 10건 pilot은 각각 원본 근거로 보존하며 서로 합치지 않는다. 새 프롬프트 실행·설명 평가·모델별 성공 수/시도 수·지표별 n·평균·비교표는 전체 계획 완료로 확정하지 않았다. 이후 보고에서는 품질·비용·시간 실측과 보안·인프라·운영·커스터마이징의 정성 분석을 구분한다.

Luna와 Motif-3도 통합 benchmark 경로의 `round_1`·`round_2`에 저장하지만 로컬의 두 회차와 합산하지 않고 서로도 합산하지 않는다. 메모리 제한은 모델에 제공하는 조건이며 Judge가 측정·강제하지 않는다. AC에 메모리 준수 검증은 포함되지 않는다.

## 재개 검사

최종 통합 저장소는 기존 요청·문제·모델·회차·완료 검사 뒤 원본 응답과 후보 파일의 일관성을 검사한다. JSON 누락/파싱 오류, 후보 누락/추출 코드 불일치, 저장한 응답 메타데이터 불일치가 있으면 재호출 전에 중단한다. API 오류 응답을 받은 경우에도 원본을 검사하고, 응답 자체가 없는 호출 예외는 원본 응답을 요구하지 않는다. 임의의 모든 원문 변조를 검출하는 암호학적 검사와는 다르다.

Cloud CLI는 모델과 무관하게 저장소별 Cloud 전용 잠금 하나를 사용한다. 프로세스 검사에서 다른 Cloud 생성·채점은 차단하고 로컬 생성·워밍업·큐·서버는 허용한다. 발견한 외부 프로세스를 종료하지 않는다. 임시 저장소·가짜 프로세스 목록과 합성 프로그램으로 양방향 병행·중복 Cloud 차단·채점 차단·FD 상속을 검증했다. [인계](../maintenance-handoff.md#현재-상태와-다음-행동)에 검증 근거를 남겼다.
