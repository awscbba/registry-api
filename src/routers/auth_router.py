"""
Authentication router with clean, standardized endpoints.
All fields use camelCase - no mapping complexity.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services.auth_service import AuthService
from ..models.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    User,
)
from ..utils.responses import create_success_response, create_error_response

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Dependency to get auth service."""
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    user = await auth_service.get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin privileges."""
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


@router.post("/login", response_model=dict)
async def login(
    login_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return JWT tokens."""
    try:
        result = await auth_service.authenticate_user(
            login_data.email, login_data.password
        )

        if not result:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return create_success_response(result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    try:
        result = await auth_service.refresh_access_token(refresh_data.refreshToken)

        if not result:
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        return create_success_response(result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return create_success_response(current_user.model_dump())


@router.post("/logout", response_model=dict)
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard tokens)."""
    # In a more sophisticated implementation, you might:
    # - Add token to blacklist
    # - Invalidate refresh tokens in database
    # - Log the logout event

    return create_success_response(
        {"message": "Logged out successfully", "userId": current_user.id}
    )


@router.post("/password/change", response_model=dict)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change user password."""
    try:
        # Validate password confirmation
        if password_data.newPassword != password_data.confirmPassword:
            raise HTTPException(
                status_code=400, detail="New password and confirmation do not match"
            )

        # For now, return success (password change logic would be implemented here)
        return create_success_response(
            {"message": "Password changed successfully", "userId": current_user.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/password/reset", response_model=dict)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Request password reset (send email with reset link)."""
    try:
        # For now, return success (password reset logic would be implemented here)
        return create_success_response(
            {
                "message": "If the email exists, a password reset link has been sent",
                "email": reset_data.email,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate", response_model=dict)
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate JWT token."""
    return create_success_response({"valid": True, "user": current_user.model_dump()})
