Here is the result of "fetch" for the Page with URL https://app.notion.com/p/3ddde5bf9074801ba56fd9356c80e820 as of 2026-09-16T00:24:20.828Z:
<page url="https://app.notion.com/p/3ddde5bf9074801ba56fd9356c80e820" icon="✅">
<ancestor-path>
<parent-page url="https://app.notion.com/p/3ddde5bf9074804c862ae9bcf4afeadf" title="8️⃣ 필수 완료 기준과 평가표"/>
<ancestor-2-page url="https://app.notion.com/p/3ddde5bf9074809787d7f6a5a5a263e7" title="프로젝트 발제 문서"/>
</ancestor-path>
<properties>
{"title":"프로젝트 수행 평가표"}
</properties>
<iconMetadata>{"type":"emoji","emoji":"✅"}</iconMetadata>
<content>
# 1. 프로젝트 요구사항 기반 평가표
<span underline="true">**구체화 버전**</span> 
<table fit-page-width="true" header-row="true">
<colgroup>
<col width="59.00000762939453">
<col>
<col>
<col>
<col>
</colgroup>
<tr>
<td>No.</td>
<td>요구사항</td>
<td>수행할 작업</td>
<td>완료 증빙·확인 항목</td>
<td>평가 관점</td>
</tr>
<tr>
<td>1</td>
<td>문제·요구사항 정의</td>
<td>서비스 Use Case, 사용자·태스크·제약조건을 정하고 필수 통과 조건과 선호 우선순위를 정의합니다.</td>
<td>문제 정의서, 사용자/태스크 설명, 한국어·보안·속도·GPU 우선순위, 최소 품질 기준</td>
<td>모델 선정 기준이 실험 전에 명확한가</td>
</tr>
<tr>
<td>2</td>
<td>후보 모델 조사</td>
<td>서로 다른 로컬 모델 2개의 특성과 실행 가능 조건을 조사합니다.</td>
<td>Model Card·License 링크, 모델 크기·Context·양자화, Ollama 태그·digest, 선정 이유</td>
<td>Use Case와 실행 환경에 맞는 서로 다른 후보를 선정했는가</td>
</tr>
<tr>
<td>3</td>
<td>실행 환경·기록 확인</td>
<td>두 후보를 CLI와 Python으로 호출하고 결과를 파일로 저장합니다.</td>
<td>기본 응답, Python·Ollama·패키지 버전, GPU·VRAM, JSON/CSV/JSONL 원본 기록</td>
<td>실제 환경에서 재현 가능하게 실행했는가</td>
</tr>
<tr>
<td>4</td>
<td>평가 질문·기준 확정</td>
<td>고정 질문 10개, 기대 결과·채점 기준, Cloud용 공통 5문항을 본 실험 전에 확정합니다.</td>
<td>질문 ID·입력·기대 결과, 정상/경계/정보 부족 사례, 동일 생성 설정</td>
<td>모델마다 공정한 비교 조건을 통제했는가</td>
</tr>
<tr>
<td>5</td>
<td>로컬 비교 실험</td>
<td>모델 2개 × 질문 10개 × 각 2회를 실행하고 워밍업과 구분합니다.</td>
<td>총 40회 응답, 설정, 성공·오류 상태, 반복 회차, 워밍업 구분</td>
<td>필수 반복 횟수와 동일 조건을 지키고 실패도 기록했는가</td>
</tr>
<tr>
<td>6</td>
<td>성능 측정·기록</td>
<td>응답 시간, 로딩 시간, 생성 속도, VRAM과 실행 조건을 수집합니다.</td>
<td>elapsed, load_duration, eval_count, eval_duration, tokens/s, size_vram, context length, CPU/GPU 적재 상태</td>
<td>측정 불가 사유를 남기고 첫 실행 지연과 일반 응답 지연을 구분했는가</td>
</tr>
<tr>
<td>7</td>
<td>품질 평가·해석</td>
<td>동일 루브릭으로 원본 응답을 채점하고 성공·실패 사례를 분석합니다.</td>
<td>질문별 점수 근거, 평균, 성공 수/전체 시도 수, 지표별 n, 대표 사례</td>
<td>점수와 원본 응답 근거·한계를 함께 설명했는가</td>
</tr>
<tr>
<td>8</td>
<td>Local–Cloud 비교</td>
<td>Cloud 모델 1개에 공통 질문 5개를 1회씩 적용합니다.</td>
<td>응답·상태·시간·토큰·예상 비용, 실제/추정 비용 구분, 반복 수 차이</td>
<td>품질·비용·보안·운영·인프라·커스터마이징을 비교했는가</td>
</tr>
<tr>
<td>9</td>
<td>최종 선정·발표</td>
<td>필수 조건과 우선순위에 따라 로컬 후보 1개를 선정합니다.</td>
<td>선택·탈락 근거, 실패 사례, 실험 한계, 운영 방식 권고</td>
<td>요구사항과 실측 근거를 연결해 합리적으로 결정했는가</td>
</tr>
<tr>
<td>10</td>
<td>제출·재실행 확인</td>
<td>저장소 하나에 코드·환경·질문·원본 기록·비교표·선정 근거를 정리합니다.</td>
<td>README, 실행 방법, 자료 위치, 팀원 기여, 재실행 기록, API 키 미포함</td>
<td>제3자가 실험 흐름과 결과를 이해·재현할 수 있는가</td>
</tr>
</table>
## 필수 완료 여부 빠른 점검
- [ ] 서로 다른 로컬 모델 2개를 선정하고 실제로 실행했습니다.
- [ ] 모델별 고정 질문 10개를 2회씩 실행하여 총 40회의 로컬 실험 기록을 남겼습니다.
- [ ] 워밍업 실행은 본 실험 결과와 분리했습니다.
- [ ] 원본 응답·성공/오류·측정값·실행 설정을 다시 읽을 수 있는 파일로 저장했습니다.
- [ ] 동일 품질 기준으로 평가하고 점수 근거를 남겼습니다.
- [ ] 모델별 성공 수/전체 시도 수와 지표별 집계 응답 수(n)를 표시했습니다.
- [ ] Cloud 모델 1개에 공통 질문 5개를 실행하고 비용·토큰·시간을 기록했습니다.
- [ ] 최종 로컬 모델과 실제 서비스 운영 권고를 구분해 제시했습니다.
- [ ] GitHub README에 실행 방법, 환경 정보, 결과 파일 위치를 정리했습니다.
- [ ] API 키·모델 가중치·가상환경 전체를 저장소에 포함하지 않았습니다.
# 2. 팀 공통 최종 검수 체크리스트
- [ ] 질문 10개, 채점 기준, 최종 선정 기준을 팀 전체가 합의했습니다.
- [ ] 모든 팀원이 모델 실행·결과 기록·채점 과정에 참여했습니다.
- [ ] 로컬 모델은 서로 다른 2개 후보를 비교했습니다.
- [ ] 기본 로컬 실험 40회와 Cloud 비교 5회가 모두 기록되어 있습니다.
- [ ] 결과에 워밍업·실패·재시도·측정 누락이 구분되어 있습니다.
- [ ] 품질 평균, 성능 평균, 성공 수/전체 시도 수, 지표별 n이 있습니다.
- [ ] 최종 모델 선택 근거가 요구사항과 실험 데이터에 연결되어 있습니다.
- [ ] Cloud와 Local을 실제 서비스에 어떻게 활용할지 운영 권고가 있습니다.
- [ ] 다른 팀원이 GitHub 저장소를 다시 실행해 확인했습니다.
- [ ] API 키 및 민감 데이터가 저장소에 포함되지 않았습니다.
</content>
</page>
