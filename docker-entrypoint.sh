#!/bin/bash
# ============================================
# Docker Entrypoint Script
# ============================================

set -e

echo "========================================"
echo "LTX2 T2I2V Lipsync - Starting..."
echo "========================================"

# ============================================
# Check CUDA
# ============================================
echo "Checking CUDA availability..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
    echo "CUDA is available"
else
    echo "WARNING: CUDA not detected"
fi

# ============================================
# Start ComfyUI in Background
# ============================================
echo "Starting ComfyUI server..."
cd /workspace/ComfyUI

python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --cuda-device 0 \
    --highvram \
    &

COMFYUI_PID=$!
echo "ComfyUI started with PID: $COMFYUI_PID"

# ============================================
# Wait for ComfyUI to be Ready
# ============================================
echo "Waiting for ComfyUI to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8188/system_stats > /dev/null; then
        echo "ComfyUI is ready!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# ============================================
# Execute Main Command
# ============================================
echo "========================================"
echo "Starting main application..."
echo "========================================"

exec "$@"