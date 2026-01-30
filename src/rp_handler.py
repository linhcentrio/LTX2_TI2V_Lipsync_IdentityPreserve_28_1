"""
RunPod Serverless Handler for LTX2 T2I2V with Lipsync

Author: Hồ Mạnh Linh (@linhcentrio)
Company: CentrioShop
License: MIT
"""

import runpod
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .comfyui_api import ComfyUIClient
from .storage import S3StorageManager
from .utils import (
    download_file,
    validate_input,
    get_duration_from_audio,
    calculate_num_frames,
    setup_logging
)

# Setup logging
logger = setup_logging()

# Environment variables
COMFYUI_URL = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
S3_BUCKET = os.getenv('S3_BUCKET_NAME')
WORKSPACE_DIR = Path('/workspace')
OUTPUT_DIR = WORKSPACE_DIR / 'output'
INPUT_DIR = WORKSPACE_DIR / 'input'
WORKFLOW_PATH = WORKSPACE_DIR / 'workflows' / 'ltx2_i2v_lipsync.json'

# Create directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize clients
comfyui_client = ComfyUIClient(COMFYUI_URL)
s3_manager = S3StorageManager(bucket_name=S3_BUCKET)


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod handler function
    
    Args:
        job: RunPod job dictionary containing input parameters
        
    Returns:
        Dictionary with status and output/error
    """
    job_input = job.get('input', {})
    job_id = job.get('id', 'unknown')
    
    logger.info(f"Starting job {job_id}")
    logger.info(f"Input parameters: {json.dumps(job_input, indent=2)}")
    
    start_time = time.time()
    
    try:
        # ============================================
        # 1. Validate Input
        # ============================================
        validation_error = validate_input(job_input)
        if validation_error:
            logger.error(f"Validation error: {validation_error}")
            return {
                "status": "error",
                "error": validation_error
            }
        
        # Extract parameters
        prompt = job_input['prompt']
        audio_url = job_input['audio_url']
        reference_image_url = job_input.get('reference_image_url')
        num_frames = job_input.get('num_frames')
        fps = job_input.get('fps', 24)
        width = job_input.get('width', 512)
        height = job_input.get('height', 768)
        cfg_scale = job_input.get('cfg_scale', 7.0)
        steps = job_input.get('steps', 30)
        seed = job_input.get('seed', -1)
        
        # ============================================
        # 2. Download Audio & Calculate Frames
        # ============================================
        logger.info("Downloading audio file...")
        audio_path = INPUT_DIR / f"{job_id}_audio.mp3"
        download_file(audio_url, audio_path)
        
        # Auto-calculate num_frames from audio duration
        if num_frames is None:
            audio_duration = get_duration_from_audio(audio_path)
            num_frames = calculate_num_frames(audio_duration, fps)
            logger.info(f"Auto-calculated num_frames: {num_frames} (duration: {audio_duration}s, fps: {fps})")
        
        # ============================================
        # 3. Download Reference Image (if provided)
        # ============================================
        reference_image_path = None
        if reference_image_url:
            logger.info("Downloading reference image...")
            reference_image_path = INPUT_DIR / f"{job_id}_reference.jpg"
            download_file(reference_image_url, reference_image_path)
        
        # ============================================
        # 4. Load ComfyUI Workflow
        # ============================================
        logger.info(f"Loading workflow from {WORKFLOW_PATH}")
        with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # ============================================
        # 5. Update Workflow Parameters
        # ============================================
        logger.info("Updating workflow parameters...")
        
        # Update text prompt node (Flux)
        for node_id, node in workflow.items():
            if node.get('class_type') == 'CLIPTextEncode':
                node['inputs']['text'] = prompt
            
            # Update LTX-2 video parameters
            elif node.get('class_type') == 'LTX2VideoGeneration':
                node['inputs'].update({
                    'num_frames': num_frames,
                    'width': width,
                    'height': height,
                    'cfg_scale': cfg_scale,
                    'steps': steps,
                    'seed': seed
                })
            
            # Update audio path
            elif node.get('class_type') == 'LoadAudio':
                node['inputs']['audio'] = str(audio_path)
            
            # Update reference image if provided
            elif node.get('class_type') == 'LoadImage' and reference_image_path:
                node['inputs']['image'] = str(reference_image_path)
        
        # ============================================
        # 6. Queue Workflow in ComfyUI
        # ============================================
        logger.info("Queueing workflow in ComfyUI...")
        prompt_id = comfyui_client.queue_prompt(workflow)
        logger.info(f"Workflow queued with prompt_id: {prompt_id}")
        
        # ============================================
        # 7. Wait for Completion
        # ============================================
        logger.info("Waiting for workflow completion...")
        success, result = comfyui_client.wait_for_completion(
            prompt_id,
            timeout=300,  # 5 minutes
            check_interval=2
        )
        
        if not success:
            error_msg = result.get('error', 'Unknown error during processing')
            logger.error(f"Workflow failed: {error_msg}")
            return {
                "status": "error",
                "error": error_msg
            }
        
        # ============================================
        # 8. Get Output Video Path
        # ============================================
        logger.info("Retrieving output video...")
        video_filename = result.get('outputs', {}).get('video', {}).get('filename')
        
        if not video_filename:
            logger.error("No video filename in result")
            return {
                "status": "error",
                "error": "No video generated"
            }
        
        video_path = OUTPUT_DIR / video_filename
        
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return {
                "status": "error",
                "error": f"Output video not found: {video_filename}"
            }
        
        # ============================================
        # 9. Upload to S3
        # ============================================
        logger.info(f"Uploading video to S3: {video_path}")
        s3_key = f"videos/{job_id}/{video_filename}"
        video_url = s3_manager.upload_file(video_path, s3_key)
        logger.info(f"Video uploaded successfully: {video_url}")
        
        # ============================================
        # 10. Calculate Metrics
        # ============================================
        processing_time = time.time() - start_time
        file_size = video_path.stat().st_size
        
        # ============================================
        # 11. Return Success Response
        # ============================================
        response = {
            "status": "success",
            "output": {
                "video_url": video_url,
                "duration": get_duration_from_audio(audio_path),
                "fps": fps,
                "frames": num_frames,
                "resolution": f"{width}x{height}",
                "file_size": file_size
            },
            "metadata": {
                "processing_time": round(processing_time, 2),
                "job_id": job_id,
                "prompt_id": prompt_id,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        }
        
        logger.info(f"Job {job_id} completed successfully in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.exception(f"Job {job_id} failed with exception")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
    
    finally:
        # Cleanup temporary files
        try:
            if audio_path and audio_path.exists():
                audio_path.unlink()
            if reference_image_path and reference_image_path.exists():
                reference_image_path.unlink()
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


if __name__ == "__main__":
    # Start RunPod serverless worker
    logger.info("Starting RunPod serverless worker...")
    runpod.serverless.start({"handler": handler})