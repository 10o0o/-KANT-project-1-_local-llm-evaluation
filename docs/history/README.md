# 정리 이력

2026-09-15에 현재 benchmark 코드와 과거 실습 자료를 분리했다. 정리 전 전체 추적 파일은 로컬 태그 `pre-cleanup-2026-09-15`에 보존했다. 이 태그는 원격에 push하지 않았다.

## 과거 코드 확인

```bash
git show pre-cleanup-2026-09-15:scripts/run_one_problem.py
git show pre-cleanup-2026-09-15:src/llm_eval/local_chat.py
git show pre-cleanup-2026-09-15:tmp/ac.py
```

태그에는 당시의 `pyproject.toml`과 `uv.lock`도 있다. 과거 코드를 실행하려면 해당 버전의 환경이 필요하며, 현재 패키지에서 과거 Ollama 실행 명령을 지원하지는 않는다.

## 코드 정리

| 이전 위치 | 처리 |
| --- | --- |
| `scripts/run_one_problem.py` | `scripts/run_benchmark.py` 진입점과 `src/llm_eval/benchmark/`로 역할 분리 |
| `scripts/run_stress_test.py` | `scripts/calibration/run_stress_test.py`로 이동; 루트 계산·출력 경로 수정 |
| `scripts/run_one_problem_old.py` | 제거; Git 이력 보존 |
| `scripts/run_local.py`, `src/scripts/ollama_chat.py` | 제거; Git 이력 보존 |
| `src/scripts/hyperclova_chat.py` | 제거; Git 이력 보존 |
| `src/llm_eval/local_chat.py`, `src/llm_eval/utils.py` | 제거; Git 이력 보존 |
| `scripts/gemma4_code_manual_test.py`, `scripts/qwen36_code_manual_test.py` | 제거; Git 이력 보존 |
| `tmp/ac.py`, `tmp/wa.py`, `tmp/re.py`, `tmp/tle.py`, `tmp/skare_correct.py` | 제거; Git 이력 보존 |
| `src/llm_eval/judge.py`의 직접 실행 블록 | 임시 파일 참조를 제거; 채점 함수 유지 |

## 자료 이동

| 이전 위치 | 현재 위치 |
| --- | --- |
| `tmp.md` | [HyperCLOVAX 실행 메모](hyperclovax-runbook.md) |
| `tmp/struktura_gemma_fixed.py` | [Gemma 수동 수정본](../../results/diagnostics/struktura/struktura_gemma_fixed.py) |
| `tmp/struktura_qwen_fixed.py` | [Qwen 수동 수정본](../../results/diagnostics/struktura/struktura_qwen_fixed.py) |
| `results/benchmark_pilot_6144/` | [pilot/6144](../../results/pilot/6144/) |
| `results/stress/` | [calibration/stress](../../results/calibration/stress/) |
| `results/<timestamp>/` | [archive/legacy-runs](../../results/archive/legacy-runs/) 아래 같은 timestamp |

결과와 수동 수정본 74개 파일의 내용은 그대로 보존했다. Timestamp 폴더에는 내용 있는 20개와 빈 폴더 1개가 있었다. 빈 폴더도 로컬에서 이동했지만 Git은 빈 디렉터리를 추적하지 않는다.

발제 원문·첨부 HTML·이전 발제·문제 데이터는 변경하지 않았다. 기록 분류가 달라져도 기존 JSON의 실행 ID·설정·판정은 소급 수정하지 않았다. 실제 모델 실행·채점이나 새 실험 성공을 뜻하는 정리가 아니다.
