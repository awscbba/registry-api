"""
Project models for the People Registry API.
Clean camelCase models with no field mapping complexity.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


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
        ..., min_length=1, max_length=2000, description="Project description"
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
        None, max_length=1000, description="Project requirements"
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

    @field_validator("endDate")
    @classmethod
    def end_date_after_start_date(cls, v, info):
        """Validate that end date is after start date."""
        if info.data.get("startDate") and v <= info.data["startDate"]:
            raise ValueError("End date must be after start date")
        return v


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

    @field_validator("endDate")
    @classmethod
    def end_date_after_start_date(cls, v, info):
        """Validate that end date is after start date."""
        if v and info.data.get("startDate") and v <= info.data["startDate"]:
            raise ValueError("End date must be after start date")
        return v


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
