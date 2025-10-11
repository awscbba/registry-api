"""
Dynamic Forms Models
Pydantic models for dynamic form builder functionality
Following clean architecture patterns established in the project
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class CustomField(BaseModel):
    """Model for custom form fields (polls)"""

    id: str = Field(..., description="Unique field identifier")
    type: Literal["poll_single", "poll_multiple"] = Field(..., description="Field type")
    question: str = Field(
        ..., min_length=1, max_length=500, description="Poll question text"
    )
    options: List[str] = Field(
        ..., min_items=2, max_items=10, description="Available options"
    )
    required: bool = Field(default=False, description="Whether field is required")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        """Validate poll options"""
        if len(set(v)) != len(v):
            raise ValueError("Poll options must be unique")
        return v


class ProjectImage(BaseModel):
    """Model for project images"""

    url: str = Field(..., description="S3 URL for the image")
    filename: str = Field(
        ..., min_length=1, max_length=255, description="Original filename"
    )
    size: int = Field(
        ..., gt=0, le=10_000_000, description="File size in bytes (max 10MB)"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate S3 URL format"""
        if not v.startswith(("https://s3.", "https://", "http://")):
            raise ValueError("Invalid image URL format")
        return v


class FormSchema(BaseModel):
    """Model for project form schema"""

    version: str = Field(default="1.0", description="Schema version")
    fields: List[CustomField] = Field(
        default_factory=list, max_items=20, description="Custom fields"
    )
    richTextDescription: str = Field(
        default="", max_length=10000, description="Markdown description"
    )

    @field_validator("fields")
    @classmethod
    def validate_unique_field_ids(cls, v):
        """Ensure field IDs are unique"""
        field_ids = [field.id for field in v]
        if len(set(field_ids)) != len(field_ids):
            raise ValueError("Field IDs must be unique")
        return v


class ProjectSubmissionBase(BaseModel):
    """Base model for project submissions"""

    projectId: str = Field(..., description="Project identifier")
    personId: str = Field(..., description="Person identifier")
    responses: Dict[str, Any] = Field(..., description="Form responses")


class ProjectSubmissionCreate(ProjectSubmissionBase):
    """Model for creating project submissions"""

    pass


class ProjectSubmission(ProjectSubmissionBase):
    """Complete project submission model"""

    id: str = Field(..., description="Unique submission identifier")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")


# Enhanced Project Models with Dynamic Forms Support
class EnhancedProjectBase(BaseModel):
    """Enhanced project base with dynamic forms support"""

    customFields: Optional[List[CustomField]] = Field(
        default=None, description="Custom form fields"
    )
    formSchema: Optional[FormSchema] = Field(default=None, description="Form schema")
    images: Optional[List[ProjectImage]] = Field(
        default=None, description="Project images"
    )


class EnhancedProjectCreate(EnhancedProjectBase):
    """Model for creating projects with dynamic forms"""

    # Inherit from existing ProjectBase when we extend it
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(
        ..., min_length=1, max_length=2000, description="Project description"
    )
    startDate: str = Field(..., description="Project start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="Project end date (YYYY-MM-DD)")
    maxParticipants: int = Field(
        ..., ge=1, le=1000, description="Maximum number of participants"
    )


class EnhancedProject(EnhancedProjectCreate):
    """Complete enhanced project model"""

    id: str = Field(..., description="Project identifier")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")
    currentParticipants: int = Field(default=0, description="Current participant count")


class ImageUploadRequest(BaseModel):
    """Model for image upload requests"""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., pattern=r"^image/(jpeg|jpg|png|gif|webp)$")
    file_size: int = Field(..., gt=0, le=10 * 1024 * 1024)  # Max 10MB


class ImageUploadResponse(BaseModel):
    """Model for image upload responses"""

    uploadUrl: str
    imageId: str
    cloudFrontUrl: str
