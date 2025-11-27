"""
Authentication router with clean, standardized endpoints.
All fields use camelCase - no mapping complexity.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services.auth_service import AuthService
from ..services.service_registry_manager import get_auth_service
from ..models.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    User,
)
from ..utils.responses import create_success_response, create_error_response

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


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
        # Log the refresh attempt for debugging
        from ..services.logging_service import logging_service, LogLevel, LogCategory

        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.AUTHENTICATION,
            message="Token refresh attempt",
            additional_data={
                "has_refresh_token": bool(refresh_data.refreshToken),
                "token_length": (
                    len(refresh_data.refreshToken) if refresh_data.refreshToken else 0
                ),
            },
        )

        result = await auth_service.refresh_access_token(refresh_data.refreshToken)
        if not result:
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )
        return create_success_response(result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        logging_service.log_structured(
            level=LogLevel.ERROR,
            category=LogCategory.AUTHENTICATION,
            message=f"Token refresh error: {str(e)}",
            additional_data={"error": str(e)},
        )
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

        # Validate and change password
        from ..utils.password_utils import hash_and_validate_password, PasswordHasher

        # Verify current password
        person = auth_service.people_repository.get_by_id(current_user.id)  # Not async
        if not person or not hasattr(person, "passwordHash") or not person.passwordHash:
            raise HTTPException(
                status_code=400, detail="Account not set up for password change"
            )

        if not PasswordHasher.verify_password(
            password_data.currentPassword, person.passwordHash
        ):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Validate and hash new password
        is_valid, new_hash, errors = hash_and_validate_password(
            password_data.newPassword
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Password validation failed: {', '.join(errors)}",
            )

        # Update password in database
        from ..models.person import PersonUpdate

        update_data = PersonUpdate(passwordHash=new_hash)
        updated_person = auth_service.people_repository.update(
            current_user.id, update_data
        )  # Not async

        if not updated_person:
            raise HTTPException(status_code=500, detail="Failed to update password")

        # Log password change
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.PASSWORD_MANAGEMENT,
            message=f"Password changed for user {current_user.id}",
            additional_data={"user_id": current_user.id},
        )

        return create_success_response(
            {"message": "Password changed successfully", "userId": current_user.id}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    reset_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Request password reset (send email with reset link)."""
    try:
        result = await auth_service.initiate_password_reset(reset_data.email)
        return create_success_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Reset password using reset token."""
    # Validate password confirmation in router
    if reset_data.newPassword != reset_data.confirmPassword:
        raise HTTPException(
            status_code=400, detail="New password and confirmation do not match"
        )

    try:
        result = await auth_service.reset_password(
            reset_data.token, reset_data.newPassword
        )
        return create_success_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate-reset-token/{token}", response_model=dict)
async def validate_reset_token(
    token: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Validate password reset token."""
    try:
        is_valid = await auth_service.validate_reset_token(token)
        return create_success_response({"valid": is_valid, "token": token})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate", response_model=dict)
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate JWT token."""
    return create_success_response({"valid": True, "user": current_user.model_dump()})


@router.put("/profile", response_model=dict)
async def update_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update current user's profile information."""
    try:
        from ..models.person import PersonUpdate, Address
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        # Build update data from request
        update_fields = {}

        # Only allow users to update their own profile fields
        allowed_fields = ["firstName", "lastName", "phone", "dateOfBirth", "address"]

        for field in allowed_fields:
            if field in profile_data:
                if field == "address" and isinstance(profile_data[field], dict):
                    # Convert address dict to Address model
                    update_fields[field] = Address(**profile_data[field])
                else:
                    update_fields[field] = profile_data[field]

        # Prevent users from updating email through this endpoint (requires verification)
        if "email" in profile_data and profile_data["email"] != current_user.email:
            raise HTTPException(
                status_code=400,
                detail="Email changes require verification. Please contact support.",
            )

        # Prevent users from updating admin status
        if "isAdmin" in profile_data:
            raise HTTPException(
                status_code=403,
                detail="Cannot modify admin status through profile update",
            )

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Update person using people repository
        update_data = PersonUpdate(**update_fields)
        updated_person = auth_service.people_repository.update(
            current_user.id, update_data
        )

        if not updated_person:
            raise HTTPException(status_code=404, detail="User not found")

        # Log profile update
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.USER_OPERATIONS,
            message=f"Profile updated for user {current_user.id}",
            additional_data={
                "user_id": current_user.id,
                "updated_fields": list(update_fields.keys()),
            },
        )

        # Return updated user data
        from ..models.person import PersonResponse

        response_data = PersonResponse(**updated_person.model_dump())

        return create_success_response(
            response_data.model_dump(), "Profile updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        logging_service.log_structured(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR_HANDLING,
            message=f"Profile update failed: {str(e)}",
            additional_data={"user_id": current_user.id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=str(e))
