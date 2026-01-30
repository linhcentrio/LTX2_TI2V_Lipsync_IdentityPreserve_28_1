# ============================================
# LTX2 T2I2V Lipsync - Docker Image
# ============================================
# Base image: RunPod PyTorch with CUDA 12.8
FROM runpod/pytorch:2.5.1-py3.11-cuda12.8.0-devel-ubuntu22.04

# Set working directory
WORKDIR /workspace

# ============================================
# System Dependencies
# ============================================
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Flash-Attention 3 (CUDA 12.8)
# ============================================
RUN pip install packaging ninja
RUN pip install flash-attn --no-build-isolation

# ============================================
# Install ComfyUI
# ============================================
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI

WORKDIR /workspace/ComfyUI

# Install ComfyUI dependencies
RUN pip install -r requirements.txt

# Install custom nodes for LTX-2
WORKDIR /workspace/ComfyUI/custom_nodes

# LTX-Video custom node
RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
WORKDIR /workspace/ComfyUI/custom_nodes/ComfyUI-LTXVideo
RUN pip install -r requirements.txt

# Wav2Lip for lipsync
WORKDIR /workspace/ComfyUI/custom_nodes
RUN git clone https://github.com/ShmuelRonen/ComfyUI-Wav2Lip.git
WORKDIR /workspace/ComfyUI/custom_nodes/ComfyUI-Wav2Lip
RUN pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt"

# IPAdapter for identity preservation
WORKDIR /workspace/ComfyUI/custom_nodes
RUN git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
WORKDIR /workspace/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus
RUN pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt"

# ============================================
# Install Application Dependencies
# ============================================
WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Copy Application Code
# ============================================
COPY src/ /workspace/src/
COPY workflows/ /workspace/workflows/

# ============================================
# Create Directories
# ============================================
RUN mkdir -p /workspace/models \
    /workspace/output \
    /workspace/input \
    /workspace/logs

# ============================================
# Environment Variables
# ============================================
ENV PYTHONUNBUFFERED=1 \
    COMFYUI_URL=http://127.0.0.1:8188 \
    CUDA_VISIBLE_DEVICES=0

# ============================================
# Expose Ports
# ============================================
EXPOSE 8188

# ============================================
# Healthcheck
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || exit 1

# ============================================
# Startup Script
# ============================================
COPY docker-entrypoint.sh /workspace/
RUN chmod +x /workspace/docker-entrypoint.sh

ENTRYPOINT ["/workspace/docker-entrypoint.sh"]

# Default command: Start RunPod handler
CMD ["python", "-u", "-m", "src.rp_handler"]