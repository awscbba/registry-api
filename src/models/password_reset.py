"""
Password reset token models for secure password reset functionality.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class PasswordResetToken(BaseModel):
    """Password reset token model for DynamoDB storage."""

    reset_token: str = Field(..., description="Unique reset token (UUID)")
    person_id: str = Field(..., description="ID of the person requesting reset")
    email: str = Field(..., description="Email address for the reset")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    is_used: bool = Field(default=False, description="Whether token has been used")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = Field(None, description="IP address of requester")
    user_agent: Optional[str] = Field(None, description="User agent of requester")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PasswordResetRequest(BaseModel):
    """Request model for password reset initiation."""

    email: str = Field(..., description="Email address to send reset link")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")


class PasswordResetValidation(BaseModel):
    """Model for validating reset tokens."""

    reset_token: str = Field(..., description="Reset token to validate")
    new_password: str = Field(..., description="New password to set")


class PasswordResetResponse(BaseModel):
    """Response model for password reset operations."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Response message")
    token_valid: Optional[bool] = Field(None, description="Whether token is valid")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class RateLimitInfo(BaseModel):
    """Rate limiting information for password reset requests."""

    email: str = Field(..., description="Email address")
    request_count: int = Field(default=0, description="Number of requests made")
    window_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_request: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Constants for password reset configuration
class PasswordResetConfig:
    """Configuration constants for password reset functionality."""

    # Token expiration time (1 hour)
    TOKEN_EXPIRY_HOURS = 1

    # Rate limiting configuration
    MAX_REQUESTS_PER_HOUR = 3  # Maximum reset requests per email per hour
    RATE_LIMIT_WINDOW_HOURS = 1  # Rate limit window duration

    # Token cleanup configuration
    CLEANUP_EXPIRED_TOKENS_HOURS = 24  # Clean up tokens older than 24 hours

    # Security configuration
    TOKEN_LENGTH = 32  # Length of generated tokens

    @classmethod
    def get_token_expiry(cls) -> datetime:
        """Get expiration time for new tokens."""
        return datetime.now(timezone.utc) + timedelta(hours=cls.TOKEN_EXPIRY_HOURS)

    @classmethod
    def get_rate_limit_window_start(cls) -> datetime:
        """Get start time for current rate limit window."""
        return datetime.now(timezone.utc) - timedelta(hours=cls.RATE_LIMIT_WINDOW_HOURS)

    @classmethod
    def is_token_expired(cls, expires_at: datetime) -> bool:
        """Check if a token is expired."""
        return datetime.now(timezone.utc) > expires_at

    @classmethod
    def generate_reset_token(cls) -> str:
        """Generate a secure reset token."""
        return str(uuid.uuid4()).replace('-', '')
