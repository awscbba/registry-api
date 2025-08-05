"""
Authentication middleware for FastAPI.
"""

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from ..utils.jwt_utils import JWTManager
from ..models.auth import AuthenticatedUser
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService as DynamoDBService

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware for protecting endpoints."""

    def __init__(self):
        self.db_service = DynamoDBService()

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> AuthenticatedUser:
        """
        Get the current authenticated user from JWT token.

        Args:
            credentials: HTTP Bearer credentials

        Returns:
            AuthenticatedUser object

        Raises:
            HTTPException: If token is invalid or user not found
        """
        token = credentials.credentials

        # Verify JWT token
        payload = JWTManager.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        try:
            person = await self.db_service.get_person(user_id)
            if not person:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if account is active
            if not getattr(person, "is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if account is locked
            if hasattr(person, "account_locked_until") and person.account_locked_until:
                from datetime import datetime, timezone

                if person.account_locked_until > datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Account is temporarily locked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # Create authenticated user object
            authenticated_user = AuthenticatedUser(
                id=person.id,
                email=person.email,
                first_name=person.first_name,
                last_name=person.last_name,
                require_password_change=getattr(
                    person, "require_password_change", False
                ),
                is_active=getattr(person, "is_active", True),
                last_login_at=getattr(person, "last_login_at", None),
            )

            return authenticated_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error",
            )

    async def get_optional_user(self, request: Request) -> Optional[AuthenticatedUser]:
        """
        Get the current user if authenticated, None otherwise.
        Useful for endpoints that work with or without authentication.

        Args:
            request: FastAPI request object

        Returns:
            AuthenticatedUser object or None
        """
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            )

            return await self.get_current_user(credentials)
        except HTTPException:
            return None
        except Exception:
            return None


# Global instance
auth_middleware = AuthMiddleware()


# Dependency functions for use in FastAPI endpoints
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthenticatedUser:
    """Dependency to get current authenticated user."""
    return await auth_middleware.get_current_user(credentials)


async def get_optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """Dependency to get current user if authenticated."""
    return await auth_middleware.get_optional_user(request)


def require_no_password_change(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Dependency that requires user to not need password change.
    Useful for endpoints that should be blocked if password change is required.
    """
    if current_user.require_password_change:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before accessing this resource",
        )
    return current_user
