#!/usr/bin/env bash
set -euo pipefail

LLAMA_ROOT="${LLAMA_ROOT:-$HOME/workspace/local-llm/runtimes/llama.cpp}"
MODEL_PATH="${QWEN36_MODEL_PATH:-$HOME/workspace/local-llm/models/qwen3.6-35b-a3b-q4_k_m/model.gguf}"

exec "$LLAMA_ROOT/build/bin/llama-server" \
  --model "$MODEL_PATH" \
  --alias qwen36 \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 32768 \
  --n-predict 30720 \
  --parallel 1 \
  --gpu-layers all \
  --n-cpu-moe 32 \
  --load-mode none \
  --flash-attn on \
  --temp 0 \
  --reasoning on \
  --reasoning-budget 26624 \
  --threads 16 \
  --threads-batch 24 \
  --cache-ram 0 \
  -lv 4
