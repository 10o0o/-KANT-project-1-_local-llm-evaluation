MODEL='hf.co/naver-ellm/HyperCLOVAX-SEED-Think-14B-GGUF:Q4_K_M'
GGUF=$(ollama show --modelfile "$MODEL" | awk '$1=="FROM" {print $2; exit}')


/home/jake/workspace/local-llm/runtimes/hyperclovax-llama.cpp/build/bin/llama-server   -m "$GGUF"   -ngl 24   -c 4096   --host 127.0.0.1   --port 8080


===

/home/jake/workspace/local-llm/runtimes/hyperclovax-llama.cpp/build/bin/llama-cli \
  -m "$GGUF" -ngl 24 -c 4096 -cnv --temp 0.5
