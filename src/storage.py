"""
S3 Storage Manager

Handles file upload/download to S3-compatible storage

Author: Hồ Mạnh Linh
"""

import boto3
import os
import logging
from pathlib import Path
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3StorageManager:
    """Manager for S3-compatible storage operations"""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None
    ):
        """
        Initialize S3 storage manager
        
        Args:
            bucket_name: S3 bucket name
            endpoint_url: S3 endpoint URL (for S3-compatible services)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
        self.endpoint_url = endpoint_url or os.getenv('S3_ENDPOINT_URL')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME must be provided")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=self.region_name
        )
        
        logger.info(f"S3 Storage Manager initialized: bucket={self.bucket_name}, region={self.region_name}")
    
    def upload_file(
        self,
        file_path: Path,
        s3_key: str,
        extra_args: Optional[dict] = None
    ) -> str:
        """
        Upload file to S3
        
        Args:
            file_path: Local file path
            s3_key: S3 object key
            extra_args: Extra arguments for upload (e.g., ContentType, ACL)
            
        Returns:
            Public URL of uploaded file
        """
        try:
            logger.info(f"Uploading {file_path} to s3://{self.bucket_name}/{s3_key}")
            
            # Default extra args
            if extra_args is None:
                extra_args = {}
            
            # Set content type based on file extension
            if 'ContentType' not in extra_args:
                content_type = self._get_content_type(file_path)
                if content_type:
                    extra_args['ContentType'] = content_type
            
            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Generate public URL
            url = self._generate_url(s3_key)
            logger.info(f"Upload successful: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def download_file(
        self,
        s3_key: str,
        local_path: Path
    ) -> Path:
        """
        Download file from S3
        
        Args:
            s3_key: S3 object key
            local_path: Local destination path
            
        Returns:
            Path to downloaded file
        """
        try:
            logger.info(f"Downloading s3://{self.bucket_name}/{s3_key} to {local_path}")
            
            # Create parent directories
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            
            logger.info(f"Download successful: {local_path}")
            return local_path
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting s3://{self.bucket_name}/{s3_key}")
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Delete successful: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            raise
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if file exists
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    def _generate_url(self, s3_key: str) -> str:
        """
        Generate public URL for S3 object
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Public URL
        """
        if self.endpoint_url:
            # Custom endpoint (e.g., DigitalOcean Spaces)
            base_url = self.endpoint_url.rstrip('/')
            return f"{base_url}/{self.bucket_name}/{s3_key}"
        else:
            # Standard AWS S3
            return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
    
    @staticmethod
    def _get_content_type(file_path: Path) -> Optional[str]:
        """
        Get content type based on file extension
        
        Args:
            file_path: File path
            
        Returns:
            Content type string or None
        """
        extension = file_path.suffix.lower()
        
        content_types = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        
        return content_types.get(extension)