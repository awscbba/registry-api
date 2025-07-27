"""
JWT utilities for token generation and validation.
"""
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets


class JWTConfig:
    """JWT configuration settings."""
    # In production, this should come from environment variables or AWS Secrets Manager
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days


# Alias for backward compatibility
JWTHandler = None

class JWTManager:
    """Handles JWT token generation and validation."""

    @staticmethod
    def create_access_token(
        subject: str,
        user_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            subject: The subject (usually user ID)
            user_data: Additional user data to include in token
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
            **user_data
        }

        encoded_jwt = jwt.encode(
            to_encode,
            JWTConfig.SECRET_KEY,
            algorithm=JWTConfig.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(subject: str) -> str:
        """
        Create a JWT refresh token.

        Args:
            subject: The subject (usually user ID)

        Returns:
            JWT refresh token string
        """
        expire = datetime.now(timezone.utc) + timedelta(days=JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(
            to_encode,
            JWTConfig.SECRET_KEY,
            algorithm=JWTConfig.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                JWTConfig.SECRET_KEY,
                algorithms=[JWTConfig.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None

    @staticmethod
    def get_token_subject(token: str) -> Optional[str]:
        """
        Extract the subject from a JWT token.

        Args:
            token: JWT token string

        Returns:
            Token subject or None if invalid
        """
        payload = JWTManager.verify_token(token)
        if payload:
            return payload.get("sub")
        return None

    @staticmethod
    def is_token_expired(token: str) -> bool:
        """
        Check if a JWT token is expired.

        Args:
            token: JWT token string

        Returns:
            True if expired, False if valid
        """
        try:
            payload = jwt.decode(
                token,
                JWTConfig.SECRET_KEY,
                algorithms=[JWTConfig.ALGORITHM],
                options={"verify_exp": False}  # Don't raise exception for expired tokens
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)
            return True
        except jwt.PyJWTError:
            return True


# Convenience functions
def create_tokens_for_user(user_id: str, user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: User ID
        user_data: User data to include in access token

    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = JWTManager.create_access_token(user_id, user_data)
    refresh_token = JWTManager.create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


# Create JWTHandler class for backward compatibility
class JWTHandler(JWTManager):
    """Backward compatibility alias for JWTManager."""
    pass
