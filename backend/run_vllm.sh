#!/bin/bash

# Run script for vLLM with Qwen3.5 4B
# Replace MODEL_ID with the exact Hugging Face model ID you wish to use if it differs.
MODEL_ID="Qwen/Qwen3.5-4B"

echo "Starting vLLM server for model: $MODEL_ID"

uv run vllm serve "$MODEL_ID" \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --max-model-len 8192 \
    --dtype auto \
    --trust-remote-code
