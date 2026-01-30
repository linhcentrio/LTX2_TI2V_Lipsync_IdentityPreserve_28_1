"""
RunPod Serverless Handler cho LTX2 Video Generation
Xử lý: Text → Image → Video với Lipsync & Identity Preservation
"""

import os
import json
import time
import runpod
import requests
import websocket
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import base64
from io import BytesIO
from PIL import Image

# Import utilities
from .comfyui_api import ComfyUIAPI
from .storage import S3Storage
from .utils import download_file, encode_image_to_base64, validate_input

# Environment variables
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
OUTPUT_DIR = Path("/workspace/output")
INPUT_DIR = Path("/workspace/input")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)


class LTX2VideoHandler:
    """Handler chính cho LTX2 video generation"""
    
    def __init__(self):
        self.comfy = ComfyUIAPI(COMFYUI_URL)
        self.storage = S3Storage(S3_BUCKET, S3_ENDPOINT) if S3_BUCKET else None
        
    def process_request(self, job_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý request chính
        
        Args:
            job_input: {
                "prompt": "text prompt cho video",
                "reference_image": "URL hoặc base64 image",
                "audio": "URL hoặc base64 audio (optional)",
                "audio_text": "Text để TTS (optional)",
                "duration": 8,
                "fps": 24,
                "resolution": "1024x1024",
                "steps": 30,
                "cfg_scale": 7.5,
                "seed": -1
            }
        
        Returns:
            {
                "status": "success",
                "video_url": "pre-signed URL",
                "metadata": {...}
            }
        """
        try:
            # 1. Validate input
            errors = validate_input(job_input)
            if errors:
                return {"error": f"Validation failed: {', '.join(errors)}"}
            
            # 2. Prepare inputs
            job_id = str(uuid.uuid4())
            prompt = job_input.get("prompt", "")
            reference_image = job_input.get("reference_image")
            audio_input = job_input.get("audio") or job_input.get("audio_text")
            
            # 3. Download/process reference image
            image_path = self._prepare_image(reference_image, job_id)
            
            # 4. Prepare audio
            audio_path = None
            if audio_input:
                audio_path = self._prepare_audio(audio_input, job_id)
            
            # 5. Load workflow
            workflow = self._load_workflow()
            
            # 6. Update workflow parameters
            workflow = self._update_workflow_params(
                workflow,
                prompt=prompt,
                image_path=image_path,
                audio_path=audio_path,
                job_input=job_input
            )
            
            # 7. Execute workflow in ComfyUI
            print(f"[{job_id}] Starting ComfyUI workflow...")
            result = self.comfy.execute_workflow(workflow)
            
            if not result.get("success"):
                return {"error": f"Workflow execution failed: {result.get('error')}"}
            
            # 8. Get output video path
            video_path = result.get("output_path")
            if not video_path or not Path(video_path).exists():
                return {"error": "Video generation failed - output not found"}
            
            # 9. Upload to S3
            video_url = None
            if self.storage:
                print(f"[{job_id}] Uploading to S3...")
                video_url = self.storage.upload_file(
                    video_path,
                    f"videos/{job_id}/output.mp4"
                )
            else:
                # Fallback: encode as base64
                with open(video_path, "rb") as f:
                    video_base64 = base64.b64encode(f.read()).decode()
                video_url = f"data:video/mp4;base64,{video_base64}"
            
            # 10. Cleanup
            self._cleanup(image_path, audio_path, video_path)
            
            return {
                "status": "success",
                "video_url": video_url,
                "job_id": job_id,
                "metadata": {
                    "prompt": prompt,
                    "duration": job_input.get("duration", 8),
                    "fps": job_input.get("fps", 24),
                    "resolution": job_input.get("resolution", "1024x1024"),
                    "processing_time": result.get("processing_time", 0)
                }
            }
            
        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}
    
    def _prepare_image(self, image_input: str, job_id: str) -> Path:
        """Download hoặc decode image"""
        image_path = INPUT_DIR / f"{job_id}_reference.png"
        
        if image_input.startswith("http"):
            download_file(image_input, image_path)
        elif image_input.startswith("data:image"):
            img_data = base64.b64decode(image_input.split(",")[1])
            img = Image.open(BytesIO(img_data))
            img.save(image_path)
        else:
            raise ValueError("Invalid image input format")
        
        return image_path
    
    def _prepare_audio(self, audio_input: str, job_id: str) -> Path:
        """Download/generate audio"""
        audio_path = INPUT_DIR / f"{job_id}_audio.wav"
        
        if audio_input.startswith("http"):
            download_file(audio_input, audio_path)
        elif audio_input.startswith("data:audio"):
            audio_data = base64.b64decode(audio_input.split(",")[1])
            with open(audio_path, "wb") as f:
                f.write(audio_data)
        else:
            self._text_to_speech(audio_input, audio_path)
        
        return audio_path
    
    def _text_to_speech(self, text: str, output_path: Path):
        """Convert text to speech"""
        try:
            from TTS.api import TTS
            tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
            tts.tts_to_file(text=text, file_path=str(output_path))
        except Exception as e:
            print(f"TTS failed: {e}, using silent audio")
            import soundfile as sf
            import numpy as np
            silence = np.zeros(16000 * 5)
            sf.write(str(output_path), silence, 16000)
    
    def _load_workflow(self) -> Dict:
        """Load ComfyUI workflow JSON"""
        workflow_path = Path("/workspace/workflows/ltx2_i2v_lipsync.json")
        with open(workflow_path, "r") as f:
            return json.load(f)
    
    def _update_workflow_params(
        self,
        workflow: Dict,
        prompt: str,
        image_path: Path,
        audio_path: Optional[Path],
        job_input: Dict
    ) -> Dict:
        """Update workflow với parameters từ request"""
        
        # Update text prompt node
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = prompt
        
        # Update image loader node
        if "10" in workflow:
            workflow["10"]["inputs"]["image"] = str(image_path)
        
        # Update audio node nếu có
        if audio_path and "12" in workflow:
            workflow["12"]["inputs"]["audio"] = str(audio_path)
        
        # Update LTX-2 parameters
        if "20" in workflow:
            workflow["20"]["inputs"].update({
                "steps": job_input.get("steps", 30),
                "cfg": job_input.get("cfg_scale", 7.5),
                "seed": job_input.get("seed", -1),
                "fps": job_input.get("fps", 24),
                "duration": job_input.get("duration", 8)
            })
        
        return workflow
    
    def _cleanup(self, *paths):
        """Cleanup temporary files"""
        for path in paths:
            if path and Path(path).exists():
                Path(path).unlink()


# RunPod Handler Function
handler_instance = LTX2VideoHandler()

def handler(job: Dict) -> Dict:
    """
    Main RunPod handler function
    
    Args:
        job: RunPod job object
    
    Returns:
        Dict với output hoặc error
    """
    job_input = job.get("input", {})
    
    print(f"Processing job: {job.get('id')}")
    print(f"Input: {json.dumps(job_input, indent=2)}")
    
    start_time = time.time()
    
    try:
        result = handler_instance.process_request(job_input)
        processing_time = time.time() - start_time
        
        if "error" in result:
            return result
        
        result["processing_time"] = processing_time
        return result
        
    except Exception as e:
        return {"error": f"Handler exception: {str(e)}"}


if __name__ == "__main__":
    print("Starting RunPod Serverless Worker...")
    print(f"ComfyUI URL: {COMFYUI_URL}")
    print(f"S3 Bucket: {S3_BUCKET}")
    
    runpod.serverless.start({"handler": handler})
