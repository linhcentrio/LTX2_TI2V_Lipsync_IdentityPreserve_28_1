"""
Unit Tests for RunPod Handler

Author: Hồ Mạnh Linh
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.rp_handler import handler
from src.comfyui_api import ComfyUIClient
from src.storage import S3StorageManager
from src.utils import (
    validate_input,
    calculate_num_frames,
    get_duration_from_audio,
    download_file
)


class TestInputValidation:
    """Test input validation"""
    
    def test_valid_input(self):
        """Test valid input passes validation"""
        job_input = {
            'prompt': 'A beautiful woman talking',
            'audio_url': 'https://example.com/audio.mp3'
        }
        
        error = validate_input(job_input)
        assert error is None
    
    def test_missing_prompt(self):
        """Test missing prompt fails validation"""
        job_input = {
            'audio_url': 'https://example.com/audio.mp3'
        }
        
        error = validate_input(job_input)
        assert error is not None
        assert 'prompt' in error
    
    def test_missing_audio_url(self):
        """Test missing audio_url fails validation"""
        job_input = {
            'prompt': 'A beautiful woman talking'
        }
        
        error = validate_input(job_input)
        assert error is not None
        assert 'audio_url' in error
    
    def test_invalid_audio_url(self):
        """Test invalid audio URL fails validation"""
        job_input = {
            'prompt': 'Test',
            'audio_url': 'not-a-valid-url'
        }
        
        error = validate_input(job_input)
        assert error is not None
    
    def test_numeric_field_validation(self):
        """Test numeric field validation"""
        job_input = {
            'prompt': 'Test',
            'audio_url': 'https://example.com/audio.mp3',
            'num_frames': 2000  # Too high
        }
        
        error = validate_input(job_input)
        assert error is not None
        assert 'num_frames' in error


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_calculate_num_frames(self):
        """Test frame calculation"""
        # 5 seconds at 24fps = 120 frames
        frames = calculate_num_frames(5.0, 24)
        assert frames == 120
        
        # 10 seconds at 30fps = 300 frames
        frames = calculate_num_frames(10.0, 30)
        assert frames == 300
    
    def test_calculate_num_frames_clamping(self):
        """Test frame clamping"""
        # Too low - should clamp to 24
        frames = calculate_num_frames(0.5, 24)
        assert frames >= 24
        
        # Too high - should clamp to 1000
        frames = calculate_num_frames(100.0, 24)
        assert frames <= 1000


class TestComfyUIClient:
    """Test ComfyUI API client"""
    
    @patch('requests.Session')
    def test_client_initialization(self, mock_session):
        """Test client initialization"""
        client = ComfyUIClient('http://localhost:8188')
        assert client.base_url == 'http://localhost:8188'
    
    @patch('requests.Session')
    def test_queue_prompt(self, mock_session):
        """Test queueing a prompt"""
        mock_response = Mock()
        mock_response.json.return_value = {'prompt_id': 'test-123'}
        mock_response.raise_for_status = Mock()
        
        mock_session.return_value.request.return_value = mock_response
        
        client = ComfyUIClient()
        workflow = {"test": "workflow"}
        
        prompt_id = client.queue_prompt(workflow)
        assert prompt_id == 'test-123'
    
    @patch('requests.Session')
    def test_health_check(self, mock_session):
        """Test health check"""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'ok'}
        mock_response.raise_for_status = Mock()
        
        mock_session.return_value.request.return_value = mock_response
        
        client = ComfyUIClient()
        is_healthy = client.health_check()
        assert is_healthy is True


class TestS3StorageManager:
    """Test S3 storage manager"""
    
    @patch('boto3.client')
    def test_initialization(self, mock_boto_client):
        """Test S3 manager initialization"""
        manager = S3StorageManager(
            bucket_name='test-bucket',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret'
        )
        
        assert manager.bucket_name == 'test-bucket'
    
    @patch('boto3.client')
    def test_generate_url(self, mock_boto_client):
        """Test URL generation"""
        manager = S3StorageManager(
            bucket_name='test-bucket',
            region_name='us-east-1'
        )
        
        url = manager._generate_url('videos/test.mp4')
        assert 'test-bucket' in url
        assert 'test.mp4' in url


class TestHandler:
    """Test main handler function"""
    
    @patch('src.rp_handler.comfyui_client')
    @patch('src.rp_handler.s3_manager')
    @patch('src.utils.download_file')
    @patch('src.utils.get_duration_from_audio')
    def test_handler_success(
        self,
        mock_get_duration,
        mock_download,
        mock_s3,
        mock_comfyui
    ):
        """Test successful handler execution"""
        # Setup mocks
        mock_get_duration.return_value = 5.0
        mock_download.return_value = Path('/tmp/audio.mp3')
        
        mock_comfyui.queue_prompt.return_value = 'prompt-123'
        mock_comfyui.wait_for_completion.return_value = (
            True,
            {
                'outputs': {
                    'video': {
                        'filename': 'output.mp4'
                    }
                }
            }
        )
        
        mock_s3.upload_file.return_value = 'https://s3.amazonaws.com/bucket/video.mp4'
        
        # Mock file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 15728640
                
                # Test job
                job = {
                    'id': 'test-job-123',
                    'input': {
                        'prompt': 'A woman talking about AI',
                        'audio_url': 'https://example.com/audio.mp3'
                    }
                }
                
                # Mock workflow file
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = '{}'
                    
                    result = handler(job)
        
        # Assertions
        assert result['status'] == 'success'
        assert 'output' in result
        assert 'video_url' in result['output']
    
    def test_handler_validation_error(self):
        """Test handler with invalid input"""
        job = {
            'id': 'test-job-456',
            'input': {
                # Missing required fields
            }
        }
        
        result = handler(job)
        
        assert result['status'] == 'error'
        assert 'error' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])