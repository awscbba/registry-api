"""
Standardized API Response Models for OpenAPI Documentation.
Provides consistent response formats across all endpoints.
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

# Generic type for response data
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response model used across all endpoints.

    This model ensures consistent response format and improves API documentation.
    """

    success: bool = Field(
        ..., description="Indicates whether the operation was successful", example=True
    )
    data: Optional[T] = Field(
        None, description="Response data (type varies by endpoint)"
    )
    message: Optional[str] = Field(
        None,
        description="Human-readable message about the operation",
        example="Operation completed successfully",
    )
    errors: Optional[List[str]] = Field(
        None,
        description="List of error messages (present only when success=false)",
        example=[],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata about the response"
    )

    class Config:
        schema_extra = {
            "examples": [
                {
                    "success": True,
                    "data": {"id": "123", "name": "John Doe"},
                    "message": "User retrieved successfully",
                    "metadata": {
                        "timestamp": "2025-01-14T03:45:00Z",
                        "version": "2.0.0",
                    },
                },
                {
                    "success": False,
                    "message": "Validation failed",
                    "errors": [
                        "Email is required",
                        "Password must be at least 8 characters",
                    ],
                    "metadata": {
                        "timestamp": "2025-01-14T03:45:00Z",
                        "error_code": "VALIDATION_ERROR",
                    },
                },
            ]
        }


class ErrorResponse(BaseModel):
    """
    Standardized error response model.

    Used for all error responses to ensure consistent error handling.
    """

    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(
        ...,
        description="Primary error message",
        example="An error occurred while processing your request",
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Detailed error messages",
        example=["Validation failed for field 'email'", "Field 'password' is required"],
    )
    error_code: Optional[str] = Field(
        None, description="Machine-readable error code", example="VALIDATION_ERROR"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional error metadata"
    )

    class Config:
        schema_extra = {
            "examples": [
                {
                    "success": False,
                    "message": "Validation failed",
                    "errors": ["Email format is invalid", "Password is too short"],
                    "error_code": "VALIDATION_ERROR",
                    "metadata": {
                        "timestamp": "2025-01-14T03:45:00Z",
                        "request_id": "req_123456",
                    },
                },
                {
                    "success": False,
                    "message": "User not found",
                    "error_code": "NOT_FOUND",
                    "metadata": {
                        "timestamp": "2025-01-14T03:45:00Z",
                        "resource": "user",
                        "resource_id": "user_123",
                    },
                },
            ]
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""

    status: str = Field(
        ..., description="Overall system health status", example="healthy"
    )
    timestamp: str = Field(
        ..., description="Timestamp of health check", example="2025-01-14T03:45:00Z"
    )
    services: Dict[str, Dict[str, Any]] = Field(
        ..., description="Individual service health status"
    )
    version: str = Field(..., description="API version", example="2.0.0")
    uptime: Optional[str] = Field(
        None, description="System uptime", example="2 days, 14 hours, 30 minutes"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-14T03:45:00Z",
                "services": {
                    "people_service": {
                        "status": "healthy",
                        "response_time": "45ms",
                        "last_check": "2025-01-14T03:45:00Z",
                    },
                    "projects_service": {
                        "status": "healthy",
                        "response_time": "32ms",
                        "last_check": "2025-01-14T03:45:00Z",
                    },
                },
                "version": "2.0.0",
                "uptime": "2 days, 14 hours, 30 minutes",
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Response model for paginated data."""

    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(
        ..., description="Total number of items across all pages", example=150
    )
    page: int = Field(..., description="Current page number (1-based)", example=1)
    limit: int = Field(..., description="Number of items per page", example=20)
    total_pages: int = Field(..., description="Total number of pages", example=8)
    has_next: bool = Field(
        ..., description="Whether there are more pages available", example=True
    )
    has_prev: bool = Field(
        ..., description="Whether there are previous pages available", example=False
    )

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {"id": "1", "name": "John Doe"},
                    {"id": "2", "name": "Jane Smith"},
                ],
                "total": 150,
                "page": 1,
                "limit": 20,
                "total_pages": 8,
                "has_next": True,
                "has_prev": False,
            }
        }


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""

    operation: str = Field(
        ..., description="Type of bulk operation performed", example="bulk_activate"
    )
    total_requested: int = Field(
        ..., description="Total number of items requested for operation", example=10
    )
    successful: int = Field(
        ..., description="Number of items successfully processed", example=8
    )
    failed: int = Field(
        ..., description="Number of items that failed processing", example=2
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of failed operations"
    )

    class Config:
        schema_extra = {
            "example": {
                "operation": "bulk_activate",
                "total_requested": 10,
                "successful": 8,
                "failed": 2,
                "errors": [
                    {"item_id": "user_123", "error": "User already active"},
                    {"item_id": "user_456", "error": "User not found"},
                ],
            }
        }


# Common HTTP status code responses for OpenAPI documentation
COMMON_RESPONSES = {
    200: {"description": "Successful operation", "model": APIResponse},
    400: {"description": "Bad request - validation failed", "model": ErrorResponse},
    401: {
        "description": "Unauthorized - authentication required",
        "model": ErrorResponse,
    },
    403: {
        "description": "Forbidden - insufficient permissions",
        "model": ErrorResponse,
    },
    404: {"description": "Not found - resource does not exist", "model": ErrorResponse},
    422: {
        "description": "Unprocessable entity - validation error",
        "model": ErrorResponse,
    },
    429: {
        "description": "Too many requests - rate limit exceeded",
        "model": ErrorResponse,
    },
    500: {"description": "Internal server error", "model": ErrorResponse},
}


# Specific response models for different data types
class PersonResponse(APIResponse):
    """API response containing person data."""

    pass


class ProjectResponse(APIResponse):
    """API response containing project data."""

    pass


class SubscriptionResponse(APIResponse):
    """API response containing subscription data."""

    pass


class AuthResponse(APIResponse):
    """API response containing authentication data."""

    pass
