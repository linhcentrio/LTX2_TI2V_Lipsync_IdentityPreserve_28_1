# ============================================
# LTX2 Video Generation - RunPod Serverless
# CUDA 12.8 + Flash-Attention 3
# ============================================

FROM nvidia/cuda:12.8.0-cudnn9-devel-ubuntu22.04 AS base

# Environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH="/usr/local/cuda/bin:${PATH}" \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# ============================================
# Stage 2: ComfyUI Installation
# ============================================
FROM base AS comfyui

WORKDIR /workspace

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    pip install -r requirements.txt

# Install Flash-Attention 3 (CUDA 12.8 compatible)
RUN pip install flash-attn==2.5.8 --no-build-isolation

# Install LTX-2 Custom Nodes
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Lightricks/ComfyUI-LTXVideo && \
    cd ComfyUI-LTXVideo && \
    pip install -r requirements.txt

# Install Lipsync Custom Nodes
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/guoyww/AnimateDiff.git && \
    cd AnimateDiff && \
    pip install -r requirements.txt

# Install Face Restoration (Identity Preservation)
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/TencentARC/GFPGAN.git && \
    cd GFPGAN && \
    pip install -r requirements.txt

# ============================================
# Stage 3: Application
# ============================================
FROM comfyui AS app

WORKDIR /workspace

# Copy application code
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY workflows/ ./workflows/

# Create directories
RUN mkdir -p /workspace/input /workspace/output /workspace/models

# Download models (optional - comment out if models are in volume)
# RUN wget -O /workspace/models/ltx2_pro.safetensors \
#     "https://huggingface.co/Lightricks/LTX-Video-2/resolve/main/ltx2_pro.safetensors"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8188/system_stats || exit 1

# Expose ports
EXPOSE 8188

# Start script
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

CMD ["/workspace/start.sh"]
