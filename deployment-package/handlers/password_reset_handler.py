"""
Password reset API handlers for FastAPI endpoints.
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.password_reset import (
    PasswordResetRequest,
    PasswordResetValidation,
    PasswordResetResponse,
)
from ..services.password_reset_service import PasswordResetService

logger = logging.getLogger(__name__)


class PasswordResetHandler:
    """Handler for password reset API endpoints."""

    def __init__(self):
        self.password_reset_service = PasswordResetService()

    async def initiate_reset(
        self, request: PasswordResetRequest, client_request: Request
    ) -> JSONResponse:
        """
        Handle password reset initiation request.

        Args:
            request: Password reset request data
            client_request: FastAPI request object for extracting client info

        Returns:
            JSONResponse with operation result
        """
        try:
            # Extract client information
            client_ip = self._get_client_ip(client_request)
            user_agent = client_request.headers.get("user-agent")

            # Add client info to request
            request.ip_address = client_ip
            request.user_agent = user_agent

            # Process reset request
            result = await self.password_reset_service.initiate_password_reset(request)

            # Return appropriate HTTP status
            status_code = 200 if result.success else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "success": result.success,
                    "message": result.message,
                    "expires_at": (
                        result.expires_at.isoformat() if result.expires_at else None
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error in initiate_reset handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while processing password reset request",
            )

    async def validate_token(self, token: str) -> JSONResponse:
        """
        Handle reset token validation request.

        Args:
            token: Reset token to validate

        Returns:
            JSONResponse with validation result
        """
        try:
            result = await self.password_reset_service.validate_reset_token(token)

            status_code = 200 if result.success else 400

            return JSONResponse(
                status_code=status_code,
                content={
                    "success": result.success,
                    "message": result.message,
                    "token_valid": result.token_valid,
                    "expires_at": (
                        result.expires_at.isoformat() if result.expires_at else None
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error in validate_token handler: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while validating reset token",
            )

    async def reset_password(
        self, validation: PasswordResetValidation, client_request: Request
    ) -> JSONResponse:
        """
        Handle password reset completion request.

        Args:
            validation: Reset token and new password
            client_request: FastAPI request object for extracting client info

        Returns:
            JSONResponse with operation result
        """
        try:
            # Extract client information
            client_ip = self._get_client_ip(client_request)
            user_agent = client_request.headers.get("user-agent")

            # Process password reset
            result = await self.password_reset_service.reset_password(
                validation=validation, ip_address=client_ip, user_agent=user_agent
            )

            status_code = 200 if result.success else 400

            return JSONResponse(
                status_code=status_code,
                content={"success": result.success, "message": result.message},
            )

        except Exception as e:
            logger.error(f"Error in reset_password handler: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Internal server error while resetting password"
            )

    async def cleanup_tokens(self) -> JSONResponse:
        """
        Handle expired token cleanup request (admin endpoint).

        Returns:
            JSONResponse with cleanup result
        """
        try:
            cleaned_count = await self.password_reset_service.cleanup_expired_tokens()

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Cleaned up {cleaned_count} expired tokens",
                    "cleaned_count": cleaned_count,
                },
            )

        except Exception as e:
            logger.error(f"Error in cleanup_tokens handler: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Internal server error while cleaning up tokens"
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


# Convenience functions for use in FastAPI routes
password_reset_handler = PasswordResetHandler()


async def handle_initiate_reset(request: PasswordResetRequest, client_request: Request):
    """Convenience function for initiating password reset."""
    return await password_reset_handler.initiate_reset(request, client_request)


async def handle_validate_token(token: str):
    """Convenience function for validating reset token."""
    return await password_reset_handler.validate_token(token)


async def handle_reset_password(
    validation: PasswordResetValidation, client_request: Request
):
    """Convenience function for resetting password."""
    return await password_reset_handler.reset_password(validation, client_request)


async def handle_cleanup_tokens():
    """Convenience function for cleaning up expired tokens."""
    return await password_reset_handler.cleanup_tokens()
