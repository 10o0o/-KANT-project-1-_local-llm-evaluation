# Luna Cloud 비교 실행

## 범위와 발제 대응

[Notion 발제 STEP 5·7](https://app.notion.com/p/3ddde5bf9074809787d7f6a5a5a263e7)과 [수행 평가표](https://app.notion.com/p/3ddde5bf9074801ba56fd9356c80e820)의 원래 기준은 Cloud 1개·공통 5문항·각 1회다. 이번에는 직접 정한 확장으로 **기존 10문항 전체를 각각 1회** 실행한다. 발제 원문은 변경하지 않는다. 이번 수행 범위는 10문항×1회이며 별도의 5문항 추가 실행이나 5문항 분모를 만들지 않는다. 일부 로컬 결과를 확인한 뒤 전체 10문항 적용을 결정한 경과를 밝히며 결과를 보기 전 5개를 선정했다고 소급하지 않는다.

모델별 로컬 20회와 Cloud 10회는 반복 수가 다르다. 동일한 문제문·지시문·공식 시간/메모리 제한·코드 추출기·Judge를 쓰며, 로컬의 좋은 회차만 고르지 않는다. 실패·NO_CODE도 유효 정답률의 분모에 포함하고 미실행은 별도로 표시한다. 로컬의 12/20(60%) 통과선을 Cloud에 적용하거나 최종 로컬 후보 선정에 Cloud를 합치지 않는다. 10문항 실행 완료 시 Cloud 유효 정답률은 유효 정답 수/10, 일반 AC 비율은 AC 수/10이다. 유효 정답은 로컬과 동일하게 AC이며 적용 시간 제한 미만인 결과다. 호출 성공 수/실제 시도 수도 따로 표시하며, 10회 완료 전에는 시도 수를 10으로 꾸미지 않는다. 설명·시간·토큰·비용 평균은 해당 근거가 있는 응답의 n을 각각 표시한다. 설명 채점·비교 집계·최종 선정은 후속 작업이다.

## 확정한 Cloud 조건

다른 저장소 `project1-python-start/02_luna_chat.py`를 참고했다. 해당 원본과 로컬 실행 코드는 수정하지 않았다.

| 항목 | 값 |
| --- | --- |
| API / 요청 모델 | OpenAI Responses API / gpt-5.6-luna |
| Reasoning | effort=max |
| max_output_tokens | 128000, 추론과 최종 답변 합계 |
| Tools / tool_choice | 빈 목록 / none |
| store / service_tier | false / default |
| Timeout / 자동 재시도 | 3600초 / 0회 |
| temperature | 보내지 않음, 서비스 기본값 적용 |
| 입력 | 로컬과 동일한 실행 제한·문제문을 포함한 단일 user prompt, 이전 답변·정답·채점 데이터 미전달 |

[Luna 공식 문서](https://developers.openai.com/api/docs/models/gpt-5.6-luna)와 [Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)를 확인했다. Cloud는 로컬 Context 65536·출력 61440·reasoning 53248와 동일 예산이 아니다. Cloud의 effort=max를 로컬 reasoning 토큰 수로 환산하지 않는다. llama.cpp 전용 종료 메시지·cache_prompt·Context 설정은 보내지 않는다. 캐시는 서비스 동작을 따르며 응답의 캐시 읽기·쓰기 토큰을 기록한다. `store=False`를 캐시 비활성화나 모든 서비스 로그 미보존으로 해석하지 않는다.

## 실행

로컬 측정과 Cloud의 코드 채점이 CPU를 함께 사용하지 않도록 **로컬 실험 종료 후 직접 실행한다**. Cloud 워밍업은 없고 모델·생성 설정은 코드에 고정한다.

`openai_secret_key`가 실행 환경에 있으면 저장소 루트에서 다음 명령을 사용한다.

```bash
uv run python scripts/run_cloud_benchmark.py --problems all
```

기존 예제 저장소의 `.env`를 사용하려면 파일을 복사하지 않고 실행할 때만 로드한다. 예제 저장소가 현재 저장소의 형제 디렉터리인 경우다.

```bash
uv run --env-file ../project1-python-start/.env python scripts/run_cloud_benchmark.py --problems all
```

선택 실행은 `--problems`에 기존 문제 ID를 쉼표로 나열한다. 이번 명령에서 선택한 ID 목록을 invocation에 남기며 전체 계획 10회와 구분한다. 중복 ID는 거부한다. 키가 없으면 요청 전에 중단한다. 키 값은 문서·코드·결과에 저장하지 않는다.

## 결과와 실패 보존

`results/benchmark/<문제 이름>/luna/round_1/` 아래에 API 원본 `response.json`, 코드가 있으면 `candidate.py`, 정리된 `result.json`을 저장한다. 원본 응답은 채점보다 먼저 저장한다. 요청 모델과 반환 모델·response ID·전체 입력·실제 전송 설정·usage·호출 상태·API 상태·판정을 구분한다.

- `call.status=success`는 completed 또는 incomplete 응답을 받았다는 뜻이다. 정답이나 생성 완료를 뜻하지 않는다. API 완료 여부는 `generation.status`와 `incomplete_details`로 확인한다.
- incomplete도 코드가 있으면 채점하고 없으면 NO_CODE다. 거절의 원문은 response.json에 보존하며 코드가 없으면 NO_CODE로 남긴다. failed 등 비정상 API 상태는 저장 후 중단한다.
- API 예외·timeout은 안전한 오류 유형·HTTP 상태와 실패까지의 시간만 기록한 뒤 중단한다. 헤더·전체 예외 문자열을 출력하거나 저장하지 않는다.
- 입력·전송 설정이 같은 완료된 성공·실패 시도는 재실행 시 건너뛴다. 기존 기록과 입력·설정이 다르면 재호출하지 않고 중단한다. 원본 실패를 성공으로 교체하지 않는다. 불완전한 폴더나 채점 처리 오류는 자동 재호출 없이 중단한다. `record_complete`는 파일 처리 완료 표시로 모델의 정답 판정과 다르다.
- 파일·기록을 삭제해서 재시도하지 않는다. 추가 실험·재시도는 별도 원본 보존과 집계 분리가 필요하며 이번 실행기는 자동 재시도를 지원하지 않는다.

네트워크 포함 전체 응답 시간은 API 호출 직전부터 반환 직후까지이며 저장·채점 시간은 제외한다. Cloud VRAM·로딩 시간·서버 generation tok/s는 API 미제공 사유와 함께 null이다. 출력 토큰÷전체 응답 시간을 로컬 생성 속도와 같은 지표로 만들지 않는다. 내부 reasoning 전문은 요청하거나 만들어 기록하지 않고 제공된 토큰 수만 보존한다.

## 비용

2026-09-16 [공식 단가](https://developers.openai.com/api/docs/models/gpt-5.6-luna)를 재확인했다. 표준 처리·일반 길이의 텍스트 입력을 대상으로 100만 토큰당 USD 입력 0.20, 캐시 읽기 0.02, 캐시 쓰기 0.25(일반 입력의 1.25배), 출력 1.20을 사용한다.

`일반 입력 = input_tokens - cached_tokens - cache_write_tokens`로 구분해 각 단가를 적용한다. reasoning 토큰은 output_tokens에 포함되므로 다시 더하지 않는다. 단가·출처·확인일·비용 종류를 결과에 함께 남긴다.

사용량·캐시 구분이 누락되거나 비정상인 경우, 응답 모델/처리 등급이 확인한 단가와 다른 경우, 입력이 272000토큰을 초과해 장문 단가가 필요한 경우에는 예상 비용을 null과 사유로 기록한다. 0토큰과 미측정은 구분한다. 단가 변경 시 실행 전 표를 다시 확인하고 코드를 갱신해야 한다. 실제 청구액은 [API 사용량](https://platform.openai.com/usage)과 별도로 대조하며 예상 비용을 실제 청구라고 표시하지 않는다.

## 검증과 남은 작업

AI의 모의 검증 결과를 참고했다. 실제 Cloud 호출·로컬 모델 호출·생성 코드 채점은 이번 구현 작업에서 하지 않았다. 이전 프롬프트의 실제 Cloud 10건은 원본 그대로 pilot으로 분리했다. 새 프롬프트 실행·설명 평가·모델별 성공 수/시도 수·지표별 n·평균·비교표는 미완료다. 이후 보고에서는 품질·비용·시간 실측과 보안·인프라·운영·커스터마이징의 정성 분석을 구분한다.

Luna도 통합 benchmark 경로의 `round_1`에 저장하지만 로컬의 두 회차와 합산하지 않는다. 메모리 제한은 모델에 제공하는 조건이며 Judge가 측정·강제하지 않는다. AC에 메모리 준수 검증은 포함되지 않는다.
