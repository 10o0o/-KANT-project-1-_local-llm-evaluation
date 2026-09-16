#!/usr/bin/env bash
set -euo pipefail

LLAMA_ROOT="${LLAMA_ROOT:-$HOME/workspace/local-llm/runtimes/llama.cpp}"
MODEL_PATH="${GEMMA4_MODEL_PATH:-$HOME/workspace/local-llm/models/gemma4-26b-a4b-it-q4_k_m/model.gguf}"

exec "$LLAMA_ROOT/build/bin/llama-server" \
  --model "$MODEL_PATH" \
  --alias gemma4 \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 65536 \
  --n-predict 61440 \
  --parallel 1 \
  --gpu-layers auto \
  --flash-attn on \
  --temp 0 \
  --reasoning on \
  --reasoning-budget 53248 \
  --cache-ram 0
