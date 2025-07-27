"""
Password management API handlers for FastAPI endpoints.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.person import PasswordUpdateRequest, PasswordUpdateResponse
from ..services.password_management_service import PasswordManagementService
from ..middleware.auth_middleware import get_current_user
from ..models.auth import AuthenticatedUser

logger = logging.getLogger(__name__)
security = HTTPBearer()


class PasswordManagementHandler:
    """Handler for password management API endpoints."""

    def __init__(self):
        self.password_service = PasswordManagementService()

    async def update_password(
        self,
        request: PasswordUpdateRequest,
        client_request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> JSONResponse:
        """
        Handle password update request for authenticated user.

        Args:
            request: Password update request data
            client_request: FastAPI request object for extracting client info
            current_user: Currently authenticated user

        Returns:
            JSONResponse with operation result
        """
        try:
            # Extract client information
            client_ip = self._get_client_ip(client_request)
            user_agent = client_request.headers.get("user-agent")

            # Update password for current user
            success, response, error = await self.password_service.update_password(
                person_id=current_user.id,
                password_request=request,
                ip_address=client_ip,
                user_agent=user_agent,
            )

            # Return appropriate HTTP status
            status_code = 200 if success else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "success": response.success,
                    "message": response.message,
                    "require_reauth": response.require_reauth,
                },
            )

        except Exception as e:
            logger.error(f"Error in update_password handler: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Internal server error while updating password"
            )

    async def validate_current_password(
        self,
        current_password: str,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> JSONResponse:
        """
        Validate current password for authenticated user.

        Args:
            current_password: Current password to validate
            current_user: Currently authenticated user

        Returns:
            JSONResponse with validation result
        """
        try:
            is_valid, error_msg = (
                await self.password_service.validate_password_change_request(
                    person_id=current_user.id, current_password=current_password
                )
            )

            status_code = 200 if is_valid else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "valid": is_valid,
                    "message": (
                        error_msg if error_msg else "Password validation successful"
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error in validate_current_password handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while validating password",
            )

    async def check_password_history(
        self, password: str, current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> JSONResponse:
        """
        Check if password has been used recently.

        Args:
            password: Password to check against history
            current_user: Currently authenticated user

        Returns:
            JSONResponse with history check result
        """
        try:
            can_use, error_msg = await self.password_service.check_password_history(
                person_id=current_user.id, password=password
            )

            status_code = 200 if can_use else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "can_use": can_use,
                    "message": error_msg if error_msg else "Password can be used",
                },
            )

        except Exception as e:
            logger.error(f"Error in check_password_history handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while checking password history",
            )

    async def force_password_change(
        self,
        person_id: str,
        client_request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> JSONResponse:
        """
        Force password change for a user (admin function).

        Args:
            person_id: ID of person to force password change for
            client_request: FastAPI request object for extracting client info
            current_user: Currently authenticated admin user

        Returns:
            JSONResponse with operation result
        """
        try:
            # Check if current user has admin privileges
            if not self._is_admin(current_user):
                raise HTTPException(
                    status_code=403, detail="Insufficient privileges for this operation"
                )

            # Extract client information
            client_ip = self._get_client_ip(client_request)
            user_agent = client_request.headers.get("user-agent")

            # Force password change
            success, error_msg = await self.password_service.force_password_change(
                person_id=person_id,
                admin_user_id=current_user.id,
                ip_address=client_ip,
                user_agent=user_agent,
            )

            status_code = 200 if success else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "success": success,
                    "message": (
                        "Password change forced successfully" if success else error_msg
                    ),
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in force_password_change handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while forcing password change",
            )

    async def generate_temporary_password(
        self,
        person_id: str,
        client_request: Request,
        length: int = 12,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> JSONResponse:
        """
        Generate temporary password for a user (admin function).

        Args:
            person_id: ID of person to generate temporary password for
            client_request: FastAPI request object for extracting client info
            length: Length of temporary password
            current_user: Currently authenticated admin user

        Returns:
            JSONResponse with operation result and temporary password
        """
        try:
            # Check if current user has admin privileges
            if not self._is_admin(current_user):
                raise HTTPException(
                    status_code=403, detail="Insufficient privileges for this operation"
                )

            # Extract client information
            client_ip = self._get_client_ip(client_request)
            user_agent = client_request.headers.get("user-agent")

            # Generate temporary password
            success, temp_password, error_msg = (
                await self.password_service.generate_temporary_password(
                    person_id=person_id,
                    admin_user_id=current_user.id,
                    length=length,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
            )

            status_code = 200 if success else 400

            response_content = {
                "success": success,
                "message": (
                    "Temporary password generated successfully"
                    if success
                    else error_msg
                ),
            }

            if success and temp_password:
                response_content["temporary_password"] = temp_password
                response_content["require_change"] = True

            return JSONResponse(status_code=status_code, content=response_content)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in generate_temporary_password handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while generating temporary password",
            )

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded IP (common in load balancer setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _is_admin(self, user: AuthenticatedUser) -> bool:
        """
        Check if user has admin privileges.

        Args:
            user: Authenticated user

        Returns:
            True if user is admin, False otherwise
        """
        # TODO: Implement proper admin role checking
        # For now, check if user has admin role or specific permissions
        return hasattr(user, "roles") and "admin" in getattr(user, "roles", [])


# Request/Response models for API endpoints
from pydantic import BaseModel, Field


class PasswordValidationRequest(BaseModel):
    """Request model for password validation."""

    current_password: str = Field(
        ..., min_length=1, description="Current password to validate"
    )


class PasswordHistoryCheckRequest(BaseModel):
    """Request model for password history checking."""

    password: str = Field(
        ..., min_length=8, description="Password to check against history"
    )


class ForcePasswordChangeRequest(BaseModel):
    """Request model for forcing password change."""

    person_id: str = Field(..., description="ID of person to force password change for")


class GenerateTemporaryPasswordRequest(BaseModel):
    """Request model for generating temporary password."""

    person_id: str = Field(
        ..., description="ID of person to generate temporary password for"
    )
    length: int = Field(
        default=12, ge=8, le=128, description="Length of temporary password"
    )


# Convenience functions for use in FastAPI routes
password_management_handler = PasswordManagementHandler()


async def handle_update_password(
    request: PasswordUpdateRequest,
    client_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Convenience function for updating password."""
    return await password_management_handler.update_password(
        request, client_request, current_user
    )


async def handle_validate_current_password(
    request: PasswordValidationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Convenience function for validating current password."""
    return await password_management_handler.validate_current_password(
        request.current_password, current_user
    )


async def handle_check_password_history(
    request: PasswordHistoryCheckRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Convenience function for checking password history."""
    return await password_management_handler.check_password_history(
        request.password, current_user
    )


async def handle_force_password_change(
    request: ForcePasswordChangeRequest,
    client_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Convenience function for forcing password change."""
    return await password_management_handler.force_password_change(
        request.person_id, client_request, current_user
    )


async def handle_generate_temporary_password(
    request: GenerateTemporaryPasswordRequest,
    client_request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Convenience function for generating temporary password."""
    return await password_management_handler.generate_temporary_password(
        request.person_id, client_request, request.length, current_user
    )
