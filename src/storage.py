"""
S3-compatible storage để upload videos
"""

import boto3
from pathlib import Path
from typing import Optional
import os


class S3Storage:
    """S3 storage client"""
    
    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None):
        self.bucket_name = bucket_name
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
    
    def upload_file(self, file_path: str, s3_key: str, expiration: int = 3600) -> str:
        """
        Upload file to S3 và return pre-signed URL
        
        Args:
            file_path: Local file path
            s3_key: S3 object key
            expiration: Pre-signed URL expiration time (seconds)
        
        Returns:
            Pre-signed URL
        """
        # Upload file
        self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
        
        # Generate pre-signed URL
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
        
        return url
