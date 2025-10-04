"""
Authentication data models with standardized camelCase fields.
No field mapping needed - direct database-to-API consistency.
"""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Schema for login response."""

    accessToken: str = Field(..., description="JWT access token")
    refreshToken: str = Field(..., description="JWT refresh token")
    user: dict = Field(..., description="User information")
    expiresIn: int = Field(..., description="Token expiration time in seconds")


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refreshToken: str = Field(..., description="Refresh token", alias="refresh_token")

    model_config = {"populate_by_name": True}  # Allow both field name and alias


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    currentPassword: str = Field(..., min_length=1, description="Current password")
    newPassword: str = Field(..., min_length=8, description="New password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Reset token")
    newPassword: str = Field(..., min_length=8, description="New password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")


class User(BaseModel):
    """User model for authentication."""

    id: str
    email: str
    firstName: str
    lastName: str
    isAdmin: bool
    isActive: bool
    roles: list[str] = Field(default_factory=list, description="User RBAC roles")
