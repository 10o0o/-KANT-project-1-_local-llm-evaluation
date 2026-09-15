#!/usr/bin/env bash
set -euo pipefail

LLAMA_ROOT="${LLAMA_ROOT:-$HOME/workspace/local-llm/runtimes/llama.cpp}"
MODEL_PATH="${QWEN36_MODEL_PATH:-$HOME/workspace/local-llm/models/qwen3.6-35b-a3b-q4_k_m/model.gguf}"

exec "$LLAMA_ROOT/build/bin/llama-server" \
  --model "$MODEL_PATH" \
  --alias qwen36 \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 8192 \
  --n-predict 6144 \
  --parallel 1 \
  --gpu-layers all \
  --n-cpu-moe 28 \
  --flash-attn on \
  --reasoning on \
  --reasoning-budget -1
