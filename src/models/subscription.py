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


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""

    status: Optional[str] = Field(None, description="Subscription status")
    isActive: Optional[bool] = Field(None, description="Whether subscription is active")


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
