"""
ComfyUI API Client

Handles communication with ComfyUI server for workflow execution

Author: Hồ Mạnh Linh
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for interacting with ComfyUI API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        """
        Initialize ComfyUI client
        
        Args:
            base_url: Base URL of ComfyUI server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        logger.info(f"ComfyUI client initialized with base_url: {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 30
    ) -> requests.Response:
        """
        Make HTTP request to ComfyUI
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            timeout: Request timeout in seconds
            
        Returns:
            Response object
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                data=data,
                json=json_data,
                timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            raise
    
    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """
        Queue a workflow for execution
        
        Args:
            workflow: ComfyUI workflow dictionary
            
        Returns:
            Prompt ID for tracking
        """
        logger.info("Queueing workflow...")
        
        payload = {
            "prompt": workflow,
            "client_id": "runpod_handler"
        }
        
        response = self._make_request(
            method="POST",
            endpoint="/prompt",
            json_data=payload
        )
        
        result = response.json()
        prompt_id = result.get('prompt_id')
        
        if not prompt_id:
            raise ValueError("No prompt_id returned from ComfyUI")
        
        logger.info(f"Workflow queued successfully: {prompt_id}")
        return prompt_id
    
    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt
        
        Args:
            prompt_id: Prompt ID to check
            
        Returns:
            History dictionary or None if not found
        """
        response = self._make_request(
            method="GET",
            endpoint=f"/history/{prompt_id}"
        )
        
        history = response.json()
        return history.get(prompt_id)
    
    def get_queue(self) -> Dict[str, Any]:
        """
        Get current queue status
        
        Returns:
            Queue information
        """
        response = self._make_request(
            method="GET",
            endpoint="/queue"
        )
        return response.json()
    
    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 300,
        check_interval: int = 2
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Wait for workflow completion
        
        Args:
            prompt_id: Prompt ID to monitor
            timeout: Maximum wait time in seconds
            check_interval: Seconds between status checks
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        logger.info(f"Waiting for prompt {prompt_id} completion (timeout: {timeout}s)...")
        
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logger.error(f"Timeout waiting for prompt {prompt_id}")
                return False, {"error": "Execution timeout"}
            
            # Check history
            history = self.get_history(prompt_id)
            
            if history:
                # Check for errors
                if 'error' in history:
                    error_msg = history['error']
                    logger.error(f"Workflow error: {error_msg}")
                    return False, {"error": error_msg}
                
                # Check if completed
                status = history.get('status', {})
                if status.get('status_str') == 'success' or 'outputs' in history:
                    logger.info(f"Workflow completed successfully")
                    return True, history
            
            # Check queue
            queue_info = self.get_queue()
            queue_running = queue_info.get('queue_running', [])
            queue_pending = queue_info.get('queue_pending', [])
            
            # Check if our prompt is in queue
            in_queue = any(
                item[1] == prompt_id 
                for item in queue_running + queue_pending
            )
            
            if not in_queue and not history:
                logger.warning(f"Prompt {prompt_id} not in queue and no history")
                time.sleep(check_interval)
                continue
            
            logger.debug(f"Still processing... (elapsed: {elapsed:.1f}s)")
            time.sleep(check_interval)
    
    def interrupt(self) -> None:
        """
        Interrupt current execution
        """
        logger.info("Sending interrupt signal...")
        self._make_request(
            method="POST",
            endpoint="/interrupt"
        )
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system stats from ComfyUI
        
        Returns:
            System statistics
        """
        response = self._make_request(
            method="GET",
            endpoint="/system_stats"
        )
        return response.json()
    
    def health_check(self) -> bool:
        """
        Check if ComfyUI server is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self.get_system_stats()
            logger.info("ComfyUI health check: OK")
            return True
        except Exception as e:
            logger.error(f"ComfyUI health check failed: {e}")
            return False