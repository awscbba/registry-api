from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration"""

    ACTIVE = "active"
    PENDING = "pending"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SubscriptionBase(BaseModel):
    """Base subscription model with common fields"""

    personId: str = Field(..., description="ID of the person subscribing")
    projectId: str = Field(..., description="ID of the project being subscribed to")
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE, description="Subscription status"
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Additional notes about the subscription"
    )


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription"""

    pass


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription"""

    status: Optional[SubscriptionStatus] = Field(
        None, description="Subscription status"
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Additional notes about the subscription"
    )


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription responses"""

    id: str = Field(..., description="Subscription unique identifier")
    createdAt: datetime = Field(..., description="Subscription creation timestamp")
    updatedAt: datetime = Field(..., description="Subscription last update timestamp")

    # Optional expanded fields for detailed responses
    personName: Optional[str] = Field(None, description="Name of the subscribed person")
    projectName: Optional[str] = Field(
        None, description="Name of the subscribed project"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SubscriptionListResponse(BaseModel):
    """Schema for subscription list responses"""

    subscriptions: list[SubscriptionResponse]
    count: int = Field(..., description="Total number of subscriptions")


class SubscriptionWithDetails(SubscriptionResponse):
    """Extended subscription response with person and project details"""

    personEmail: Optional[str] = Field(
        None, description="Email of the subscribed person"
    )
    personPhone: Optional[str] = Field(
        None, description="Phone of the subscribed person"
    )
    projectDescription: Optional[str] = Field(
        None, description="Description of the subscribed project"
    )
    projectStartDate: Optional[str] = Field(
        None, description="Start date of the subscribed project"
    )
    projectEndDate: Optional[str] = Field(
        None, description="End date of the subscribed project"
    )
