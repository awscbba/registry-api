"""
Image Upload router - handles S3 image upload endpoints
Clean architecture implementation using service layer
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends

from ..models.dynamic_forms import ImageUploadRequest, ImageUploadResponse
from ..services.s3_image_service import S3ImageService
from ..services.service_registry_manager import get_service_registry
from ..utils.responses import create_success_response

router = APIRouter(prefix="/v2/images", tags=["Image Upload"])


def get_s3_image_service() -> S3ImageService:
    """Get S3 image service instance"""
    # For now, create directly since it's not in service registry yet
    return S3ImageService()


@router.post("/upload-url", response_model=dict)
async def get_presigned_upload_url(
    request: ImageUploadRequest,
    s3_service: S3ImageService = Depends(get_s3_image_service),
):
    """Generate presigned URL for S3 image upload."""
    try:
        # Validate file type
        if not s3_service.validate_image_file_type(request.content_type):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
            )

        # Validate file size
        if not s3_service.validate_image_file_size(request.file_size):
            raise HTTPException(
                status_code=400, detail="File too large. Maximum size is 10MB."
            )

        # Generate presigned URL
        upload_result = s3_service.generate_presigned_upload_url(
            request.filename, request.content_type
        )

        # Get CloudFront URL
        cloudfront_url = s3_service.get_image_cloudfront_url(request.filename)

        # Generate image ID
        image_id = str(uuid.uuid4())

        response_data = ImageUploadResponse(
            uploadUrl=upload_result["upload_url"],
            imageId=image_id,
            cloudFrontUrl=cloudfront_url,
        )

        return create_success_response(response_data.model_dump())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
