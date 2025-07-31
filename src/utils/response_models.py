"""
Standardized response models for consistent API responses across v1 and v2.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class BaseAPIResponse(BaseModel):
    """Base response model with common fields."""

    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "v1"  # Default to v1 for backward compatibility


class DataResponse(BaseAPIResponse):
    """Response model for single data items."""

    data: Dict[str, Any]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ListResponse(BaseAPIResponse):
    """Response model for list data."""

    data: List[Dict[str, Any]]
    count: int
    total: Optional[int] = None  # For paginated responses

    def __init__(self, data: List[Dict[str, Any]], **kwargs):
        super().__init__(data=data, count=len(data), **kwargs)


class ErrorResponse(BaseAPIResponse):
    """Response model for errors."""

    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseAPIResponse):
    """Response model for health checks."""

    status: str = "healthy"
    service: str
    checks: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseAPIResponse):
    """Response model for paginated data."""

    data: List[Dict[str, Any]]
    pagination: Dict[str, Any]

    def __init__(
        self,
        data: List[Dict[str, Any]],
        page: int = 1,
        limit: int = 100,
        total: Optional[int] = None,
        **kwargs,
    ):
        pagination = {"page": page, "limit": limit, "count": len(data)}

        if total is not None:
            pagination["total"] = total
            pagination["pages"] = (total + limit - 1) // limit
            pagination["has_next"] = page * limit < total
            pagination["has_prev"] = page > 1

        super().__init__(data=data, pagination=pagination, **kwargs)


# Response factory functions for consistent creation
class ResponseFactory:
    """Factory for creating standardized responses."""

    @staticmethod
    def success_data(data: Dict[str, Any], version: str = "v1") -> DataResponse:
        """Create successful data response."""
        return DataResponse(data=data, version=version)

    @staticmethod
    def success_list(data: List[Dict[str, Any]], version: str = "v1") -> ListResponse:
        """Create successful list response."""
        return ListResponse(data=data, version=version)

    @staticmethod
    def paginated(
        data: List[Dict[str, Any]],
        page: int = 1,
        limit: int = 100,
        total: Optional[int] = None,
        version: str = "v1",
    ) -> PaginatedResponse:
        """Create paginated response."""
        return PaginatedResponse(
            data=data, page=page, limit=limit, total=total, version=version
        )

    @staticmethod
    def health(service: str, checks: Optional[Dict[str, Any]] = None) -> HealthResponse:
        """Create health check response."""
        return HealthResponse(service=service, checks=checks)

    @staticmethod
    def error(
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        version: str = "v1",
    ) -> ErrorResponse:
        """Create error response."""
        return ErrorResponse(
            error=error_code, message=message, details=details, version=version
        )


# Legacy response helpers for backward compatibility
def create_v1_response(data: Any, success: bool = True) -> Dict[str, Any]:
    """Create v1-style response for backward compatibility."""
    if isinstance(data, list):
        return {"success": success, "data": data, "count": len(data)}
    else:
        return {"success": success, "data": data}


def create_v2_response(
    data: Any, success: bool = True, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create v2-style response with enhanced metadata."""
    response = {
        "success": success,
        "version": "v2",
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }

    if isinstance(data, list):
        response["count"] = len(data)

    if metadata:
        response["metadata"] = metadata

    return response


# Specific response models for common API patterns
class SubscriptionResponse(BaseAPIResponse):
    """Standardized subscription response."""

    subscriptions: List[Dict[str, Any]]
    count: int

    def __init__(self, subscriptions: List[Dict[str, Any]], **kwargs):
        super().__init__(
            subscriptions=subscriptions, count=len(subscriptions), **kwargs
        )


class ProjectResponse(BaseAPIResponse):
    """Standardized project response."""

    projects: List[Dict[str, Any]]
    count: int

    def __init__(self, projects: List[Dict[str, Any]], **kwargs):
        super().__init__(projects=projects, count=len(projects), **kwargs)


class PersonResponse(BaseAPIResponse):
    """Standardized person response."""

    people: List[Dict[str, Any]]
    count: int

    def __init__(self, people: List[Dict[str, Any]], **kwargs):
        super().__init__(people=people, count=len(people), **kwargs)
