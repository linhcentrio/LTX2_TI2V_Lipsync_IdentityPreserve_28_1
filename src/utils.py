"""
Helper utilities
"""

import requests
from pathlib import Path
import base64
from typing import List, Dict, Any


def download_file(url: str, output_path: Path):
    """Download file từ URL"""
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def encode_image_to_base64(image_path: Path) -> str:
    """Encode image thành base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def validate_input(job_input: Dict[str, Any]) -> List[str]:
    """
    Validate input parameters
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    if not job_input.get("prompt"):
        errors.append("'prompt' is required")
    
    if not job_input.get("reference_image"):
        errors.append("'reference_image' is required")
    
    # Validate numeric ranges
    duration = job_input.get("duration", 8)
    if not (1 <= duration <= 20):
        errors.append("'duration' must be between 1 and 20 seconds")
    
    fps = job_input.get("fps", 24)
    if fps not in [24, 30, 60]:
        errors.append("'fps' must be 24, 30, or 60")
    
    return errors
