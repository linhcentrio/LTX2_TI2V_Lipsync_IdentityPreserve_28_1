"""
Utility Functions

Helper functions for file handling, validation, etc.

Author: Hồ Mạnh Linh
"""

import requests
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import mimetypes

logger = logging.getLogger(__name__)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger(__name__)


def download_file(
    url: str,
    output_path: Path,
    timeout: int = 120
) -> Path:
    """
    Download file from URL
    
    Args:
        url: File URL
        output_path: Local output path
        timeout: Download timeout in seconds
        
    Returns:
        Path to downloaded file
    """
    logger.info(f"Downloading {url} to {output_path}")
    
    try:
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with streaming
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        # Write to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = output_path.stat().st_size
        logger.info(f"Download complete: {output_path} ({file_size} bytes)")
        
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        raise


def validate_input(job_input: Dict[str, Any]) -> Optional[str]:
    """
    Validate job input parameters
    
    Args:
        job_input: Job input dictionary
        
    Returns:
        Error message if validation fails, None if valid
    """
    # Required fields
    if 'prompt' not in job_input:
        return "Missing required field: 'prompt'"
    
    if 'audio_url' not in job_input:
        return "Missing required field: 'audio_url'"
    
    # Validate prompt
    prompt = job_input['prompt']
    if not isinstance(prompt, str) or len(prompt.strip()) == 0:
        return "'prompt' must be a non-empty string"
    
    # Validate audio_url
    audio_url = job_input['audio_url']
    if not isinstance(audio_url, str) or not audio_url.startswith(('http://', 'https://')):
        return "'audio_url' must be a valid HTTP(S) URL"
    
    # Validate optional numeric fields
    numeric_fields = {
        'num_frames': (1, 1000),
        'fps': (1, 60),
        'width': (64, 2048),
        'height': (64, 2048),
        'cfg_scale': (1.0, 30.0),
        'steps': (1, 150),
        'seed': (-1, 2147483647)
    }
    
    for field, (min_val, max_val) in numeric_fields.items():
        if field in job_input:
            value = job_input[field]
            if not isinstance(value, (int, float)):
                return f"'{field}' must be a number"
            if not (min_val <= value <= max_val):
                return f"'{field}' must be between {min_val} and {max_val}"
    
    # Validate reference_image_url if provided
    if 'reference_image_url' in job_input:
        ref_url = job_input['reference_image_url']
        if ref_url and not isinstance(ref_url, str):
            return "'reference_image_url' must be a string"
        if ref_url and not ref_url.startswith(('http://', 'https://')):
            return "'reference_image_url' must be a valid HTTP(S) URL"
    
    return None


def get_duration_from_audio(audio_path: Path) -> float:
    """
    Get duration of audio file in seconds
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds
    """
    try:
        # Use ffprobe to get duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        duration = float(result.stdout.strip())
        logger.info(f"Audio duration: {duration}s")
        return duration
        
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.warning(f"Failed to get audio duration: {e}, using default 5.0s")
        return 5.0


def calculate_num_frames(duration: float, fps: int = 24) -> int:
    """
    Calculate number of frames from duration and FPS
    
    Args:
        duration: Duration in seconds
        fps: Frames per second
        
    Returns:
        Number of frames
    """
    num_frames = int(duration * fps)
    
    # Clamp to reasonable values
    num_frames = max(24, min(num_frames, 1000))
    
    logger.info(f"Calculated {num_frames} frames for {duration}s @ {fps}fps")
    return num_frames


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: File path
        
    Returns:
        File size in MB
    """
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return round(size_mb, 2)


def validate_file_type(file_path: Path, allowed_types: list) -> bool:
    """
    Validate file type by extension
    
    Args:
        file_path: File path
        allowed_types: List of allowed extensions (e.g., ['.mp4', '.avi'])
        
    Returns:
        True if file type is allowed
    """
    extension = file_path.suffix.lower()
    return extension in allowed_types