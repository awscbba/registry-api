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

    # Password field for creation (excluded from API responses)
    password: Optional[str] = Field(None, min_length=8, exclude=True)
    passwordHash: Optional[str] = Field(None, exclude=True)  # For internal use


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

    # Security fields for admin operations
    failedLoginAttempts: Optional[int] = None
    accountLockedUntil: Optional[datetime] = None

    # Password fields (excluded from API responses)
    password: Optional[str] = Field(None, min_length=8, exclude=True)
    passwordHash: Optional[str] = Field(None, exclude=True)


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
    roles: List[str] = Field(default_factory=list, description="User RBAC roles")
    createdAt: datetime
    updatedAt: datetime
    lastLoginAt: Optional[datetime] = None

    # Security fields (for admin use)
    failedLoginAttempts: int = Field(default=0)
    accountLockedUntil: Optional[datetime] = None
    lastPasswordChange: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PersonInternal(PersonResponse):
    """Internal person model with sensitive fields (never exposed via API)."""

    passwordHash: Optional[str] = Field(None, exclude=True)
    passwordSalt: Optional[str] = Field(None, exclude=True)
    passwordHistory: List[str] = Field(default_factory=list, exclude=True)
    emailVerificationToken: Optional[str] = Field(None, exclude=True)

    model_config = {"from_attributes": True}


# Alias for backward compatibility
Person = PersonResponse
