"""
Project models for the People Registry API.
Clean camelCase models with no field mapping complexity.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr


class ProjectStatus(str, Enum):
    """Project status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectBase(BaseModel):
    """Base project model with common fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(
        ..., min_length=1, max_length=5000, description="Project description"
    )
    startDate: str = Field(..., description="Project start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="Project end date (YYYY-MM-DD)")
    maxParticipants: int = Field(
        ..., ge=1, le=1000, description="Maximum number of participants"
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.PENDING, description="Project status"
    )
    category: Optional[str] = Field(
        None, max_length=100, description="Project category"
    )
    location: Optional[str] = Field(
        None, max_length=200, description="Project location"
    )
    requirements: Optional[str] = Field(
        None, max_length=5000, description="Project requirements"
    )
    registrationEndDate: Optional[str] = Field(
        None, description="Registration end date (YYYY-MM-DD)"
    )
    isEnabled: Optional[bool] = Field(
        True, description="Whether the project is enabled"
    )
    formSchema: Optional[Dict[str, Any]] = Field(
        None, description="Dynamic form schema for enhanced project features"
    )
    richText: Optional[str] = Field(
        None, max_length=10000, description="Rich text content (HTML, max 10KB)"
    )
    enableSubscriptionNotifications: Optional[bool] = Field(
        True, description="Enable email notifications when users subscribe"
    )
    notificationEmails: Optional[List[EmailStr]] = Field(
        default_factory=list,
        description="Additional admin emails to notify on new subscriptions",
    )

    @field_validator("richText")
    @classmethod
    def validate_rich_text_size(cls, v):
        """Validate rich text content size."""
        if v is not None:
            # Check character count
            if len(v) > 10000:
                raise ValueError(
                    "Rich text content is too long (maximum 10,000 characters allowed)"
                )

            # Check byte size (HTML can be larger in bytes than characters)
            byte_size = len(v.encode("utf-8"))
            if byte_size > 15000:  # 15KB byte limit
                raise ValueError(
                    "Rich text content is too large (maximum 15KB allowed)"
                )

        return v

    @field_validator("endDate")
    @classmethod
    def end_date_after_start_date(cls, v, info):
        """Validate that end date is not before start date."""
        if info.data.get("startDate") and v < info.data["startDate"]:
            raise ValueError("End date cannot be before start date")
        return v

    @model_validator(mode="after")
    def validate_form_schema(self):
        """Validate formSchema size and richTextDescription length."""
        if self.formSchema:
            # Check total JSON size (approximate)
            import json

            json_str = json.dumps(self.formSchema)
            if len(json_str) > 50000:  # 50KB limit
                raise ValueError("Form schema is too large (max 50KB)")

            # Check richTextDescription specifically
            rich_text = self.formSchema.get("richTextDescription", "")
            if isinstance(rich_text, str) and len(rich_text) > 10000:
                raise ValueError(
                    "Rich text description is too long (max 10,000 characters)"
                )

        return self


class ProjectCreate(ProjectBase):
    """Model for creating a new project."""

    pass


class ProjectUpdate(BaseModel):
    """Model for updating an existing project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    maxParticipants: Optional[int] = Field(None, ge=1, le=1000)
    status: Optional[ProjectStatus] = None
    category: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=200)
    requirements: Optional[str] = Field(None, max_length=1000)
    registrationEndDate: Optional[str] = None
    isEnabled: Optional[bool] = None
    formSchema: Optional[Dict[str, Any]] = None
    richText: Optional[str] = Field(None, max_length=10000)
    enableSubscriptionNotifications: Optional[bool] = None
    notificationEmails: Optional[List[EmailStr]] = None

    @field_validator("richText")
    @classmethod
    def validate_rich_text_size(cls, v):
        """Validate rich text content size."""
        if v is not None:
            # Check character count
            if len(v) > 10000:
                raise ValueError(
                    "Rich text content is too long (maximum 10,000 characters allowed)"
                )

            # Check byte size (approximate)
            byte_size = len(v.encode("utf-8"))
            if byte_size > 15 * 1024:  # 15KB
                raise ValueError(
                    "Rich text content is too large (maximum 15KB allowed)"
                )

        return v

    # Note: Date validation is handled in the service layer for updates
    # since we need to compare against existing project data


class ProjectResponse(ProjectBase):
    """Model for project responses."""

    id: str = Field(..., description="Unique project identifier")
    currentParticipants: int = Field(
        default=0, description="Current number of participants"
    )
    createdAt: str = Field(..., description="Creation timestamp")
    updatedAt: str = Field(..., description="Last update timestamp")
    createdBy: str = Field(..., description="ID of user who created the project")

    model_config = {"from_attributes": True}


class Project(ProjectResponse):
    """Complete project model for internal use."""

    pass
