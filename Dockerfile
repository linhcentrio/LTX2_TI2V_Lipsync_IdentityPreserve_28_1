# ============================================
# LTX2 T2I2V Lipsync - Clean Dockerfile
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
    aria2 \
    ffmpeg \
    libsndfile1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Custom Nodes (Match Notebook)
# ============================================
WORKDIR /comfyui/custom_nodes

# 1. ComfyUI KJNodes - Utility nodes
RUN git clone --branch kj1.2.6 https://github.com/Isi-dev/ComfyUIKJNodes.git && \
    cd ComfyUIKJNodes && \
    pip install -r requirements.txt

# 2. ComfyUI GGUF - Load quantized models
RUN git clone --branch ComfyUIGGUF22012026 https://github.com/Isi-dev/ComfyUIGGUF.git && \
    cd ComfyUIGGUF && \
    pip install -r requirements.txt

# 3. LTX-Video - Core video generation with BUILT-IN lipsync
# LTX-2 handles lipsync natively via audio conditioning
# No need for external Wav2Lip or other lipsync nodes
RUN git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git && \
    cd ComfyUI-LTXVideo && \
    pip install -r requirements.txt

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
    COMFYUI_PATH=/comfyui \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

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