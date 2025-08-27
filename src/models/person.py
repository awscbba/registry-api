"""
Person data models with standardized camelCase fields.
No field mapping needed - direct database-to-API consistency.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class Address(BaseModel):
    """Address model with camelCase fields."""

    street: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")
    postalCode: str = Field(default="")  # Standardized to camelCase
    country: str = Field(default="")


class PersonCreate(BaseModel):
    """Schema for creating a new person."""

    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=20)
    dateOfBirth: str = Field(..., description="Date in YYYY-MM-DD format")
    address: Address
    isAdmin: bool = Field(default=False)


class PersonUpdate(BaseModel):
    """Schema for updating an existing person."""

    firstName: Optional[str] = Field(None, min_length=1, max_length=100)
    lastName: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    dateOfBirth: Optional[str] = None
    address: Optional[Address] = None
    isAdmin: Optional[bool] = None
    isActive: Optional[bool] = None
    requirePasswordChange: Optional[bool] = None


class PersonResponse(BaseModel):
    """Schema for person API responses."""

    id: str
    firstName: str
    lastName: str
    email: str
    phone: str
    dateOfBirth: str
    address: Address
    isAdmin: bool
    isActive: bool
    requirePasswordChange: bool
    emailVerified: bool
    createdAt: datetime
    updatedAt: datetime
    lastLoginAt: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Alias for backward compatibility
Person = PersonResponse
