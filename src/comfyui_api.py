"""
ComfyUI API Client để tương tác với ComfyUI server
"""

import json
import time
import requests
import websocket
from typing import Dict, Any, Optional
from pathlib import Path


class ComfyUIAPI:
    """Client để gọi ComfyUI API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url
        self.client_id = "runpod-serverless"
        
    def execute_workflow(self, workflow: Dict, timeout: int = 600) -> Dict[str, Any]:
        """
        Execute ComfyUI workflow và đợi kết quả
        
        Args:
            workflow: ComfyUI workflow JSON
            timeout: Timeout trong seconds
        
        Returns:
            Dict với success status và output path
        """
        start_time = time.time()
        
        try:
            # Queue prompt
            prompt_id = self._queue_prompt(workflow)
            print(f"Queued prompt: {prompt_id}")
            
            # Monitor progress qua WebSocket
            output_path = self._monitor_progress(prompt_id, timeout)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "output_path": output_path,
                "processing_time": processing_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _queue_prompt(self, workflow: Dict) -> str:
        """Queue workflow vào ComfyUI"""
        url = f"{self.base_url}/prompt"
        
        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["prompt_id"]
    
    def _monitor_progress(self, prompt_id: str, timeout: int) -> str:
        """Monitor workflow execution qua WebSocket"""
        ws_url = f"ws://{self.base_url.split('//')[1]}/ws?clientId={self.client_id}"
        
        ws = websocket.create_connection(ws_url)
        start_time = time.time()
        output_path = None
        
        try:
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Workflow execution timeout after {timeout}s")
                
                message = ws.recv()
                if not message:
                    continue
                
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "progress":
                    value = data["data"]["value"]
                    max_val = data["data"]["max"]
                    print(f"Progress: {value}/{max_val}")
                
                elif msg_type == "executing":
                    node = data["data"]["node"]
                    if node is None:
                        print("Workflow execution completed!")
                        break
                
                elif msg_type == "execution_error":
                    error_msg = data["data"].get("exception_message", "Unknown error")
                    raise RuntimeError(f"ComfyUI execution error: {error_msg}")
            
            output_path = self._get_output_file(prompt_id)
            return output_path
            
        finally:
            ws.close()
    
    def _get_output_file(self, prompt_id: str) -> str:
        """Lấy output file path từ history"""
        url = f"{self.base_url}/history/{prompt_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        history = response.json()
        outputs = history[prompt_id]["outputs"]
        
        for node_id, output in outputs.items():
            if "videos" in output:
                video_info = output["videos"][0]
                filename = video_info["filename"]
                subfolder = video_info.get("subfolder", "")
                
                output_dir = Path("/workspace/ComfyUI/output")
                if subfolder:
                    output_dir = output_dir / subfolder
                
                return str(output_dir / filename)
        
        raise FileNotFoundError("No video output found in workflow results")
    
    def check_health(self) -> bool:
        """Check if ComfyUI server is running"""
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return response.status_code == 200
        except:
            return False
