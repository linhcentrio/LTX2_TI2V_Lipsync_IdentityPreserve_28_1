# ============================================
# LTX2 T2I2V Lipsync - Optimized Dockerfile
# ============================================
# Base: RunPod ComfyUI with CUDA support
FROM runpod/comfyui:latest

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
# Install Flash-Attention 3 (Optional)
# ============================================
# Uncomment if you need Flash-Attention 3
# RUN pip install packaging ninja && \
#     pip install flash-attn --no-build-isolation

# ============================================
# Install LTX-Video Custom Node
# ============================================
WORKDIR /comfyui/custom_nodes

# LTX-Video custom node
RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git && \
    cd ComfyUI-LTXVideo && \
    pip install -r requirements.txt

# Wav2Lip for lipsync
RUN git clone https://github.com/ShmuelRonen/ComfyUI-Wav2Lip.git && \
    cd ComfyUI-Wav2Lip && \
    (pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt for Wav2Lip")

# IPAdapter for identity preservation
RUN git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git && \
    cd ComfyUI_IPAdapter_plus && \
    (pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt for IPAdapter")

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
    CUDA_VISIBLE_DEVICES=0 \
    COMFYUI_PATH=/comfyui

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