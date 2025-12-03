"""
Subscription data models with standardized camelCase fields.
No field mapping needed - direct database-to-API consistency.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""

    personId: str = Field(..., min_length=1, description="ID of the person subscribing")
    projectId: str = Field(
        ..., min_length=1, description="ID of the project to subscribe to"
    )
    status: str = Field(default="active", description="Subscription status")
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional notes or comments from subscriber",
    )


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""

    status: Optional[str] = Field(None, description="Subscription status")
    isActive: Optional[bool] = Field(None, description="Whether subscription is active")
    notes: Optional[str] = Field(
        None, max_length=1000, description="Additional notes or comments"
    )


class SubscriptionResponse(BaseModel):
    """Schema for subscription API responses."""

    id: str
    personId: str
    projectId: str
    status: str
    subscriptionDate: str
    isActive: bool
    createdAt: str
    updatedAt: str
    notes: Optional[str] = None


class Subscription(BaseModel):
    """Internal subscription model for business logic."""

    id: str
    personId: str
    projectId: str
    status: str = "active"
    subscriptionDate: str
    isActive: bool = True
    createdAt: str
    updatedAt: str
    notes: Optional[str] = None


class EnrichedSubscriptionResponse(SubscriptionResponse):
    """Subscription response enriched with related entity details."""

    # Project details
    projectName: Optional[str] = None
    projectDescription: Optional[str] = None
    projectStatus: Optional[str] = None

    # Person details
    personName: Optional[str] = None
    personEmail: Optional[str] = None
    personFirstName: Optional[str] = None
    personLastName: Optional[str] = None
