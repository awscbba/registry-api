"""
Standardized error handling utilities for consistent API responses.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class StandardErrorHandler:
    """Centralized error handling for consistent API responses across all Lambda functions."""

    @staticmethod
    def internal_server_error(
        operation: str,
        error: Exception,
        person_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """
        Create standardized 500 Internal Server Error response.

        Args:
            operation: The operation that failed (e.g., "updating password")
            error: The original exception
            person_id: Optional person ID for context
            additional_context: Optional additional context for logging
        """
        # Create context for logging
        context = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        if person_id:
            context["person_id"] = person_id

        if additional_context:
            context.update(additional_context)

        # Log the error with context
        logger.error(f"Internal server error during {operation}", extra=context)

        # Return standardized HTTPException
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"An error occurred while {operation}",
                "operation": operation,
            },
        )

    @staticmethod
    def bad_request_error(
        message: str,
        error_code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ) -> HTTPException:
        """Create standardized 400 Bad Request response."""
        detail = {"error": error_code, "message": message}

        if details:
            detail["details"] = details

        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    @staticmethod
    def not_found_error(
        resource: str, resource_id: Optional[str] = None
    ) -> HTTPException:
        """Create standardized 404 Not Found response."""
        message = f"{resource} not found"
        if resource_id:
            message += f" with ID: {resource_id}"

        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NOT_FOUND",
                "message": message,
                "resource": resource,
                "resource_id": resource_id,
            },
        )

    @staticmethod
    def unauthorized_error(message: str = "Authentication required") -> HTTPException:
        """Create standardized 401 Unauthorized response."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": message},
        )

    @staticmethod
    def forbidden_error(message: str = "Access denied") -> HTTPException:
        """Create standardized 403 Forbidden response."""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": message},
        )

    @staticmethod
    def conflict_error(
        message: str, details: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """Create standardized 409 Conflict response."""
        detail = {"error": "CONFLICT", "message": message}

        if details:
            detail["details"] = details

        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


# Convenience functions for common error patterns
def handle_database_error(
    operation: str, error: Exception, person_id: Optional[str] = None
) -> HTTPException:
    """Handle database operation errors with consistent logging and response."""
    return StandardErrorHandler.internal_server_error(
        operation=operation,
        error=error,
        person_id=person_id,
        additional_context={"component": "database"},
    )


def handle_validation_error(
    message: str, field_errors: Optional[Dict[str, str]] = None
) -> HTTPException:
    """Handle validation errors with field-specific details."""
    return StandardErrorHandler.bad_request_error(
        message=message,
        error_code="VALIDATION_ERROR",
        details={"field_errors": field_errors} if field_errors else None,
    )


def handle_authentication_error(message: str = "Invalid credentials") -> HTTPException:
    """Handle authentication failures."""
    return StandardErrorHandler.unauthorized_error(message)


def handle_authorization_error(
    message: str = "Insufficient permissions",
) -> HTTPException:
    """Handle authorization failures."""
    return StandardErrorHandler.forbidden_error(message)
