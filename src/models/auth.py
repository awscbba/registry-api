"""
Authentication models for login, token management, and security.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict
    require_password_change: bool = False


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for token operations."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SecurityEvent(BaseModel):
    """Model for security events and audit logging."""

    person_id: str
    action: str  # LOGIN_SUCCESS, LOGIN_FAILED, PASSWORD_CHANGE, etc.
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool
    details: Optional[dict] = None


class AccountLockout(BaseModel):
    """Model for account lockout information."""

    person_id: str
    failed_attempts: int
    locked_until: Optional[datetime] = None
    last_attempt_at: datetime
    ip_addresses: List[str] = []


class AuthenticatedUser(BaseModel):
    """Model representing an authenticated user."""

    id: str
    email: str
    first_name: str
    last_name: str
    require_password_change: bool = False
    is_active: bool = True
    last_login_at: Optional[datetime] = None
