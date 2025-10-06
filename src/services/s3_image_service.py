"""
S3 Image Service - Business logic for image upload and management
Handles S3 operations and CloudFront URL generation
"""

import boto3
import uuid
from typing import Dict, List
from ..models.dynamic_forms import ProjectImage


class S3ImageService:
    """Service for S3 image operations"""

    def __init__(self):
        self.bucket_name = "project-images-bucket"  # Will be configurable
        self.cloudfront_domain = "d1234567890.cloudfront.net"  # Will be configurable
        self.s3_client = None  # Lazy initialization

    def _get_s3_client(self):
        """Get S3 client with lazy initialization"""
        if not self.s3_client:
            self.s3_client = boto3.client("s3")
        return self.s3_client

    def generate_presigned_upload_url(
        self, filename: str, content_type: str
    ) -> Dict[str, str]:
        """Generate presigned URL for image upload"""
        # Validate file type and size will be done by caller
        s3_key = f"images/{uuid.uuid4()}/{filename}"

        s3_client = self._get_s3_client()
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        return {"upload_url": presigned_url, "key": s3_key, "bucket": self.bucket_name}

    def validate_image_file_type(self, content_type: str) -> bool:
        """Validate image file type"""
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]

        if content_type not in allowed_types:
            raise ValueError(f"Invalid image file type: {content_type}")

        return True

    def validate_image_file_size(self, file_size: int) -> bool:
        """Validate image file size (max 10MB)"""
        max_size = 10 * 1024 * 1024  # 10MB

        if file_size <= 0 or file_size > max_size:
            raise ValueError(
                f"Invalid file size: {file_size}. Must be between 1 byte and 10MB"
            )

        return True

    def get_image_cloudfront_url(self, s3_key: str) -> str:
        """Get CloudFront URL for uploaded image"""
        return f"https://{self.cloudfront_domain}/{s3_key}"

    def delete_unused_images(self, s3_keys: List[str]) -> bool:
        """Delete unused images from S3"""
        s3_client = self._get_s3_client()

        for key in s3_keys:
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)

        return True

    def create_project_image_model(
        self, s3_key: str, filename: str, file_size: int, cloudfront_url: str
    ) -> ProjectImage:
        """Create ProjectImage model from S3 data"""
        return ProjectImage(url=cloudfront_url, filename=filename, size=file_size)
