# Qwen llama.cpp 시작 로그 (2026-09-16 적재 조정)

2026-09-16 09:02~09:51에 Qwen 서버의 적재(offload)와 Context를 조정하면서 남은 llama.cpp 시작 로그 7건이다. `-lv 4` 진단 로그 레벨로 받았다.

**본 실험 로그가 아니다.** 본 실험 80회는 Context 65,536·출력 61,440·reasoning 53,248에서 생성했고, 아래 로그는 그 이전 12,288/8,192 단계의 조정 기록이다. 이 로그의 수치를 본 실험 실행 조건으로 소급하지 않는다. 실행별 조건은 각 `results/benchmark/<문제>/<모델>/round_<회차>/result.json`을 따른다.

| 파일 | n_ctx_seq | CUDA0 모델 버퍼 (MiB) | 비고 |
| --- | ---: | ---: | --- |
| `qwen36-manual-offload.log` | 12,288 | 7,094.32 | 최초 |
| `qwen36-manual-offload-2.log` | 12,288 | 7,094.32 | |
| `qwen36-manual-offload-test-A.log` | 8,192 | 7,094.32 | |
| `qwen36-manual-offload-test-B.log` | 12,288 | 6,230.32 | |
| `qwen36-manual-offload-test-C.log` | 12,288 | **5,366.32** | [실행 환경](../../../docs/operations/environment.md#이후-qwen-시작-로그-인용)이 인용한 값과 일치 |
| `qwen36-manual-offload-test-D.log` | — | — | 텐서 적재 중 중단되어 Context·버퍼 줄이 없다 |
| `qwen36-manual-offload-test-E.log` | 8,192 | 7,094.32 | |

일곱 건 모두 `offloaded 41/41 layers to GPU`와 `reasoning budget=512 tokens`로 시작했다. 41/41 표기와 CUDA_Host 버퍼가 함께 나타나므로 전체 GPU 전용 적재로 읽지 않는다.

`test-C`에는 GGUF `file size = 19.01 GiB`, `Q4_K - Medium`, `arch = qwen35moe`, `model params = 34.66 B`, `n_ctx = 12288`, `CUDA0 5366.32 MiB`, `CUDA_Host 14096.81 MiB`가 그대로 있다. 다만 `fit` 계산 줄(projected total, will leave … MiB, no changes needed)은 **이 7건 어디에도 없다.** 실행 환경 문서의 fit 관련 행은 여전히 첨부 해석문 인용이며 저장소 로그로 대조되지 않는다.
