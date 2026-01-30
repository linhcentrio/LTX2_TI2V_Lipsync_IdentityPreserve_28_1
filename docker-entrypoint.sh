#!/bin/bash
# ============================================
# Docker Entrypoint Script - Optimized for RunPod ComfyUI
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
    echo "✅ CUDA is available"
else
    echo "⚠️  WARNING: CUDA not detected"
fi

# ============================================
# Check ComfyUI Installation
# ============================================
if [ -d "/comfyui" ]; then
    echo "✅ ComfyUI found at /comfyui"
    COMFYUI_DIR="/comfyui"
elif [ -d "/workspace/ComfyUI" ]; then
    echo "✅ ComfyUI found at /workspace/ComfyUI"
    COMFYUI_DIR="/workspace/ComfyUI"
else
    echo "❌ ERROR: ComfyUI not found!"
    exit 1
fi

# ============================================
# Start ComfyUI in Background
# ============================================
echo "Starting ComfyUI server..."
cd "$COMFYUI_DIR"

# Start ComfyUI with optimized settings
python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --highvram \
    --preview-method auto \
    &

COMFYUI_PID=$!
echo "✅ ComfyUI started with PID: $COMFYUI_PID"

# ============================================
# Wait for ComfyUI to be Ready
# ============================================
echo "Waiting for ComfyUI to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://127.0.0.1:8188/system_stats > /dev/null 2>&1; then
        echo "✅ ComfyUI is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT+1))
    echo "⏳ Waiting... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ ERROR: ComfyUI failed to start within $(($MAX_ATTEMPTS * 2)) seconds"
    exit 1
fi

# ============================================
# Display System Info
# ============================================
echo "========================================"
echo "📊 System Information"
echo "========================================"
echo "Python version: $(python --version)"
echo "PyTorch version: $(python -c 'import torch; print(torch.__version__)')"
echo "CUDA available: $(python -c 'import torch; print(torch.cuda.is_available())')"
if python -c 'import torch; print(torch.cuda.is_available())' | grep -q True; then
    echo "CUDA version: $(python -c 'import torch; print(torch.version.cuda)')"
    echo "GPU count: $(python -c 'import torch; print(torch.cuda.device_count())')"
    echo "GPU name: $(python -c 'import torch; print(torch.cuda.get_device_name(0))')"
fi
echo "========================================"

# ============================================
# Execute Main Command
# ============================================
echo "🚀 Starting main application..."
echo "========================================"

cd /workspace
exec "$@"