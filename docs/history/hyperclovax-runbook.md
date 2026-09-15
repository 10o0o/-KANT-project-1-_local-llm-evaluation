# HyperCLOVAX 실행 메모

현재 benchmark에서는 사용하지 않는다. NAVER llama.cpp로 진단하던 당시의 명령을 보존했다. 아래 절대 경로는 당시 PC 기준이며 현재 실행 가능 여부를 다시 확인한 것은 아니다. 후보 제외 경위는 [모델 조사](../models.md#제외-이력-hyperclova)에 있다.

## 당시 메모 원문

```text
MODEL='hf.co/naver-ellm/HyperCLOVAX-SEED-Think-14B-GGUF:Q4_K_M'
GGUF=$(ollama show --modelfile "$MODEL" | awk '$1=="FROM" {print $2; exit}')


/home/jake/workspace/local-llm/runtimes/hyperclovax-llama.cpp/build/bin/llama-server   -m "$GGUF"   -ngl 24   -c 4096   --host 127.0.0.1   --port 8080


===

/home/jake/workspace/local-llm/runtimes/hyperclovax-llama.cpp/build/bin/llama-cli \
  -m "$GGUF" -ngl 24 -c 4096 -cnv --temp 0.5

```
