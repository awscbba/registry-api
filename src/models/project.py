from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ProjectStatus(str, Enum):
    """Project status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectBase(BaseModel):
    """Base project model with common fields"""

    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(
        ..., min_length=1, max_length=1000, description="Project description"
    )
    startDate: str = Field(..., description="Project start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="Project end date (YYYY-MM-DD)")
    maxParticipants: int = Field(
        ..., ge=1, le=1000, description="Maximum number of participants"
    )
    status: ProjectStatus = Field(
        default=ProjectStatus.ACTIVE, description="Project status"
    )


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Project name"
    )
    description: Optional[str] = Field(
        None, min_length=1, max_length=1000, description="Project description"
    )
    startDate: Optional[str] = Field(
        None, description="Project start date (YYYY-MM-DD)"
    )
    endDate: Optional[str] = Field(None, description="Project end date (YYYY-MM-DD)")
    maxParticipants: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum number of participants"
    )
    status: Optional[ProjectStatus] = Field(None, description="Project status")


class ProjectResponse(ProjectBase):
    """Schema for project responses"""

    id: str = Field(..., description="Project unique identifier")
    createdAt: datetime = Field(..., description="Project creation timestamp")
    updatedAt: datetime = Field(..., description="Project last update timestamp")
    createdBy: str = Field(..., description="User who created the project")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProjectListResponse(BaseModel):
    """Schema for project list responses"""

    projects: list[ProjectResponse]
    count: int = Field(..., description="Total number of projects")
