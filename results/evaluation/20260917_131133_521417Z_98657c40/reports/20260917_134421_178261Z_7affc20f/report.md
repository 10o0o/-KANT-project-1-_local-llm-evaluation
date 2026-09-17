# 평가 비교표

평가 ID: `20260917_131133_521417Z_98657c40`
전체 평가 기록 완료: True / 로컬 지표 비교 준비: True

미생성·미검토는 실패나 0점이 아닙니다. 미완료 비율은 계획 분모 대비 현재 확인한 값입니다.

| 모델 | 기록/계획 | 미생성 | 호출 실패 | NO_CODE | 공식 AC | 프로젝트 AC | 유효 정답/계획 | 2배 진단 AC/대상 | 최소 수정 통과 | 로컬 60% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen36 | 20/20 | 0 | 0 | 2 | 12 | 14 | 14/20 | 0/0 | 0 | True |
| gemma4 | 20/20 | 0 | 0 | 3 | 9 | 9 | 9/20 | 0/0 | 4 | False |
| luna | 20/20 | 0 | 0 | 0 | 15 | 16 | 16/20 | 0/0 | 2 | 미확정/비대상 |
| motif3 | 20/20 | 0 | 2 | 0 | 13 | 13 | 13/20 | 0/0 | 0 | 미확정/비대상 |

| 모델 | 설명 평균(n) | 설명 미검토 | 성공 응답 평균 초(n) | 시간 누락 | 실패 경과 평균 초(n) | 수정 검토/대상 | 수정 시도 | 2배 미실행 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen36 | 1.300000 (20) | 0 | 427.497752 (20) | 0 | — (0) | 4/4 | 0 | 0 |
| gemma4 | 1.700000 (20) | 0 | 1606.308795 (20) | 0 | — (0) | 8/8 | 4 | 0 |
| luna | 2.000000 (20) | 0 | 254.368520 (20) | 0 | — (0) | 4/4 | 3 | 0 |
| motif3 | 1.555556 (18) | 0 | 245.709363 (18) | 0 | 475.691820 (2) | 5/5 | 0 | 0 |

로컬 지표 순서(동률은 같은 묶음): [['qwen36'], ['gemma4']]
지표 비교 순서이며 최종 선정이 아닙니다. License·환경 등 필수 조건과 실제 도입 판단은 직접 확인하세요.

정책은 생성 진행 중 결정되었습니다. 공식 1배 결과를 보존하며 Tezina·Pet·Ucionica·Skijanje만 평가 제한을 완화합니다.

| 원본 항목 | 공식 판정 | 프로젝트 판정 | 근거 | 공식/평가 제한(초) | 2배 진단 | 수정 통과 |
| --- | --- | --- | --- | --- | --- | --- |
| skare/qwen36/round_1 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| skare/qwen36/round_2 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| cokolada/qwen36/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| cokolada/qwen36/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/qwen36/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/qwen36/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/qwen36/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/qwen36/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/qwen36/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/qwen36/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/qwen36/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/qwen36/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tezina/qwen36/round_1 | TLE | AC | limit_2x | 2.0/4 | — | False |
| tezina/qwen36/round_2 | TLE | AC | limit_2x | 2.0/4 | — | False |
| pet/qwen36/round_1 | TLE | TLE | limit_2x | 1.0/2 | — | False |
| pet/qwen36/round_2 | TLE | TLE | limit_2x | 1.0/2 | — | False |
| ucionica/qwen36/round_1 | WA | WA | limit_2x | 1.5/3 | — | False |
| ucionica/qwen36/round_2 | WA | WA | limit_2x | 1.5/3 | — | False |
| skijanje/qwen36/round_1 | NO_CODE | NO_CODE | baseline_1x | 1.0/2 | — | False |
| skijanje/qwen36/round_2 | NO_CODE | NO_CODE | baseline_1x | 1.0/2 | — | False |
| skare/gemma4/round_1 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| skare/gemma4/round_2 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| cokolada/gemma4/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| cokolada/gemma4/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/gemma4/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/gemma4/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/gemma4/round_1 | WA | WA | baseline_1x | 1.0/1.0 | — | True |
| tomahawk/gemma4/round_2 | NO_CODE | NO_CODE | baseline_1x | 1.0/1.0 | — | False |
| struktura/gemma4/round_1 | WA | WA | baseline_1x | 1.0/1.0 | — | True |
| struktura/gemma4/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/gemma4/round_1 | RE | RE | baseline_1x | 1.0/1.0 | — | True |
| prepisivanje/gemma4/round_2 | RE | RE | baseline_1x | 1.0/1.0 | — | True |
| tezina/gemma4/round_1 | AC | AC | baseline_1x | 2.0/4 | — | False |
| tezina/gemma4/round_2 | AC | AC | baseline_1x | 2.0/4 | — | False |
| pet/gemma4/round_1 | WA | WA | limit_2x | 1.0/2 | — | False |
| pet/gemma4/round_2 | WA | WA | limit_2x | 1.0/2 | — | False |
| ucionica/gemma4/round_1 | WA | WA | baseline_1x | 1.5/3 | — | False |
| ucionica/gemma4/round_2 | WA | WA | baseline_1x | 1.5/3 | — | False |
| skijanje/gemma4/round_1 | NO_CODE | NO_CODE | baseline_1x | 1.0/2 | — | False |
| skijanje/gemma4/round_2 | NO_CODE | NO_CODE | baseline_1x | 1.0/2 | — | False |
| skare/luna/round_1 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| skare/luna/round_2 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| cokolada/luna/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| cokolada/luna/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/luna/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/luna/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/luna/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/luna/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/luna/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/luna/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/luna/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/luna/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tezina/luna/round_1 | AC | AC | baseline_1x | 2.0/4 | — | False |
| tezina/luna/round_2 | RE | RE | baseline_1x | 2.0/4 | — | True |
| pet/luna/round_1 | AC | AC | baseline_1x | 1.0/2 | — | False |
| pet/luna/round_2 | RE | RE | baseline_1x | 1.0/2 | — | True |
| ucionica/luna/round_1 | TLE | AC | limit_2x | 1.5/3 | — | False |
| ucionica/luna/round_2 | AC | AC | baseline_1x | 1.5/3 | — | False |
| skijanje/luna/round_1 | TLE | TLE | limit_2x | 1.0/2 | — | False |
| skijanje/luna/round_2 | TLE | TLE | limit_2x | 1.0/2 | — | False |
| skare/motif3/round_1 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| skare/motif3/round_2 | AC | AC | baseline_1x | 3.0/3.0 | — | False |
| cokolada/motif3/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| cokolada/motif3/round_2 | WA | WA | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/motif3/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| dzeparac/motif3/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/motif3/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tomahawk/motif3/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/motif3/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| struktura/motif3/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/motif3/round_1 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| prepisivanje/motif3/round_2 | AC | AC | baseline_1x | 1.0/1.0 | — | False |
| tezina/motif3/round_1 | AC | AC | baseline_1x | 2.0/4 | — | False |
| tezina/motif3/round_2 | AC | AC | baseline_1x | 2.0/4 | — | False |
| pet/motif3/round_1 | WA | WA | limit_2x | 1.0/2 | — | False |
| pet/motif3/round_2 | TLE | TLE | limit_2x | 1.0/2 | — | False |
| ucionica/motif3/round_1 | TLE | TLE | limit_2x | 1.5/3 | — | False |
| ucionica/motif3/round_2 | TLE | TLE | limit_2x | 1.5/3 | — | False |
| skijanje/motif3/round_1 | CALL_ERROR | CALL_ERROR | baseline_1x | 1.0/2 | — | False |
| skijanje/motif3/round_2 | CALL_ERROR | CALL_ERROR | baseline_1x | 1.0/2 | — | False |
