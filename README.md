# 🎬 LTX2 Text-to-Image-to-Video với Lipsync & Identity Preservation

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![RunPod](https://img.shields.io/badge/RunPod-Serverless-orange.svg)](https://www.runpod.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **RunPod Serverless Handler** tích hợp ComfyUI workflow để tạo video từ text với **LTX-2 model**, kết hợp **lipsync** và **identity preservation**.

## 🌟 Tính Năng

### ✨ Core Features
- 🎨 **Text-to-Image-to-Video**: Text → Ảnh (Flux) → Video (LTX-2)
- 🎭 **Identity Preservation**: Giữ nguyên khuôn mặt nhân vật
- 🎤 **Lipsync**: Đồng bộ môi với audio (Wav2Lip)
- ⚡ **Flash-Attention 3**: Tối ưu CUDA 12.8 cho A100/H100
- 📦 **S3 Storage**: Upload/download tự động
- 🐳 **Docker Ready**: Deploy dễ dàng trên RunPod

### 🚀 Technical Stack
- **LTX-2**: Mô hình video generation mới nhất
- **Flux**: Text-to-Image quality cao
- **ComfyUI**: Visual workflow engine
- **RunPod Serverless**: Scalable GPU inference
- **Flash-Attention 3**: 2-3x faster training/inference

## 📋 Yêu Cầu Hệ Thống

### Hardware
- **GPU**: NVIDIA A100 (40GB/80GB) hoặc H100
- **VRAM**: Tối thiểu 24GB
- **RAM**: 32GB+
- **Storage**: 100GB+ SSD

### Software
- **CUDA**: 12.8+
- **Python**: 3.10+
- **Docker**: 24.0+
- **ComfyUI**: Latest version

## 🔧 Cài Đặt

### 1️⃣ Clone Repository

```bash
git clone https://github.com/linhcentrio/LTX2_TI2V_Lipsync_IdentityPreserve_28_1.git
cd LTX2_TI2V_Lipsync_IdentityPreserve_28_1
```

### 2️⃣ Cài Đặt Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt
```

### 3️⃣ Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env với credentials của bạn
nano .env
```

### 4️⃣ Download Models

```bash
# LTX-2 model
wget -P models/ https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.safetensors

# Flux model
wget -P models/ https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors

# Lipsync models
wget -P models/ https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth
```

## 🐳 Docker Deployment

### Build Image

```bash
# Build Docker image
docker build -t ltx2-lipsync:latest .

# Or use docker-compose
docker-compose build
```

### Run Container

```bash
# Run with docker-compose
docker-compose up -d

# Or manual docker run
docker run -d \
  --gpus all \
  -p 8188:8188 \
  -v $(pwd)/models:/workspace/models \
  -v $(pwd)/output:/workspace/output \
  --env-file .env \
  ltx2-lipsync:latest
```

## 🚀 RunPod Deployment

### Deploy to RunPod Serverless

```bash
# Login to RunPod
runpodctl login

# Deploy endpoint
runpodctl deploy \
  --name ltx2-lipsync \
  --image your-dockerhub-username/ltx2-lipsync:latest \
  --gpu-type "NVIDIA A100" \
  --gpu-count 1 \
  --min-workers 0 \
  --max-workers 3
```

### Test Endpoint

```python
import runpod

# Configure endpoint
runpod.api_key = "your-runpod-api-key"
endpoint = runpod.Endpoint("ENDPOINT_ID")

# Run inference
result = endpoint.run({
    "input": {
        "prompt": "A beautiful woman talking about AI technology",
        "audio_url": "https://example.com/audio.mp3",
        "reference_image_url": "https://example.com/face.jpg",
        "num_frames": 120,
        "fps": 24
    }
})

print(f"Video URL: {result['output']['video_url']}")
```

## 📖 API Documentation

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | ✅ | Text mô tả video |
| `audio_url` | string | ✅ | URL file audio (.mp3, .wav) |
| `reference_image_url` | string | ❌ | URL ảnh khuôn mặt tham chiếu |
| `num_frames` | integer | ❌ | Số frames (default: 120) |
| `fps` | integer | ❌ | FPS (default: 24) |
| `width` | integer | ❌ | Chiều rộng (default: 512) |
| `height` | integer | ❌ | Chiều cao (default: 768) |
| `cfg_scale` | float | ❌ | CFG scale (default: 7.0) |
| `steps` | integer | ❌ | Số steps (default: 30) |
| `seed` | integer | ❌ | Random seed (default: -1) |

### Output Format

```json
{
  "status": "success",
  "output": {
    "video_url": "https://s3.amazonaws.com/bucket/video_123.mp4",
    "duration": 5.0,
    "fps": 24,
    "frames": 120,
    "resolution": "512x768",
    "file_size": 15728640
  },
  "metadata": {
    "processing_time": 45.2,
    "gpu_time": 38.5,
    "model_version": "ltx-2-v0.9",
    "timestamp": "2026-01-30T15:30:00Z"
  }
}
```

## 📁 Project Structure

```
LTX2_TI2V_Lipsync_IdentityPreserve_28_1/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── rp_handler.py            # RunPod serverless handler
│   ├── comfyui_api.py           # ComfyUI API client
│   ├── storage.py               # S3 storage manager
│   └── utils.py                 # Utility functions
├── workflows/
│   └── ltx2_i2v_lipsync.json    # ComfyUI workflow definition
├── tests/
│   ├── __init__.py
│   └── test_handler.py          # Unit tests
├── .github/
│   └── workflows/
│       └── deploy.yml           # CI/CD pipeline
├── models/                       # Model storage (gitignored)
├── output/                       # Output videos (gitignored)
├── Dockerfile                    # Docker configuration
├── docker-compose.yml           # Docker Compose setup
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Test specific file
pytest tests/test_handler.py -v
```

### Local Testing

```bash
# Start ComfyUI
cd /path/to/ComfyUI
python main.py --listen 0.0.0.0 --port 8188

# Test handler locally
python -c "
import json
from src.rp_handler import handler

job = {
    'input': {
        'prompt': 'A woman explaining AI concepts',
        'audio_url': 'https://example.com/audio.mp3'
    }
}

result = handler(job)
print(json.dumps(result, indent=2))
"
```

## 🎯 Workflow Details

### Pipeline Steps

1. **Text-to-Image** (Flux)
   - Input: Text prompt
   - Output: High-quality image (512x768)

2. **Image-to-Video** (LTX-2)
   - Input: Generated image + prompt
   - Output: Video frames (120 frames @ 24fps)

3. **Lipsync** (Wav2Lip)
   - Input: Video + Audio
   - Output: Synced video với lip movement

4. **Identity Preservation**
   - Face detection & tracking
   - Identity consistency across frames

### Performance Benchmarks

| GPU | Resolution | Frames | Time | Cost/Run |
|-----|------------|--------|------|----------|
| A100 40GB | 512x768 | 120 | ~45s | $0.08 |
| A100 80GB | 768x1024 | 240 | ~90s | $0.15 |
| H100 | 1024x1024 | 240 | ~60s | $0.20 |

## 🔐 Security

### Environment Variables

Không commit file `.env` chứa credentials. Sử dụng `.env.example` làm template.

### S3 Permissions

Cấu hình IAM role với permissions tối thiểu:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

## 🐛 Troubleshooting

### Common Issues

#### 1. CUDA Out of Memory

```bash
# Giảm batch size hoặc resolution
# Trong workflow JSON, điều chỉnh:
"batch_size": 1
"width": 512
"height": 512
```

#### 2. ComfyUI Connection Failed

```bash
# Kiểm tra ComfyUI đang chạy
curl http://localhost:8188/system_stats

# Restart ComfyUI
pkill -f "python.*main.py"
cd /workspace/ComfyUI && python main.py --listen 0.0.0.0
```

#### 3. Model Loading Error

```bash
# Verify model files
ls -lh models/*.safetensors

# Re-download if corrupted
rm models/ltx-video-2b-v0.9.safetensors
wget -P models/ [model_url]
```

## 📊 Monitoring

### Logs

```bash
# View RunPod logs
runpodctl logs ENDPOINT_ID

# Docker logs
docker-compose logs -f

# Application logs
tail -f /workspace/logs/app.log
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📜 License

Distributed under MIT License. See `LICENSE` for more information.

## 👤 Author

**Hồ Mạnh Linh** - [@linhcentrio](https://github.com/linhcentrio)

- Company: CentrioShop
- GitHub: [linhcentrio](https://github.com/linhcentrio)

## 🙏 Acknowledgments

- [LTX-2](https://github.com/Lightricks/LTX-Video) - Video generation model
- [Flux](https://github.com/black-forest-labs/flux) - Text-to-Image
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Workflow engine
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) - Lipsync technology
- [RunPod](https://www.runpod.io/) - GPU infrastructure

## 📞 Support

Nếu gặp vấn đề, vui lòng:
- Open [GitHub Issue](https://github.com/linhcentrio/LTX2_TI2V_Lipsync_IdentityPreserve_28_1/issues)
- Email: support@example.com

---

⭐ **Star project này nếu bạn thấy hữu ích!** ⭐