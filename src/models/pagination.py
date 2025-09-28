"""
Enterprise pagination models with clean architecture compliance.
Standardized pagination across all domain entities.
"""

from typing import Generic, TypeVar, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

T = TypeVar("T")


class SortDirection(str, Enum):
    """Sort direction enumeration."""

    ASC = "asc"
    DESC = "desc"


class PaginationRequest(BaseModel):
    """Standard pagination request parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    pageSize: int = Field(
        default=10, ge=1, le=100, description="Items per page (max 100)"
    )
    sortBy: Optional[str] = Field(default=None, description="Field to sort by")
    sortDirection: SortDirection = Field(
        default=SortDirection.ASC, description="Sort direction"
    )
    search: Optional[str] = Field(default=None, description="Search term")
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional filters"
    )


class PaginationMetadata(BaseModel):
    """Pagination metadata for responses."""

    currentPage: int = Field(..., description="Current page number")
    pageSize: int = Field(..., description="Items per page")
    totalItems: int = Field(..., description="Total number of items")
    totalPages: int = Field(..., description="Total number of pages")
    hasNextPage: bool = Field(..., description="Whether there is a next page")
    hasPreviousPage: bool = Field(..., description="Whether there is a previous page")
    startIndex: int = Field(..., description="Start index of current page items")
    endIndex: int = Field(..., description="End index of current page items")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(..., description="Page items")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls, items: List[T], total_items: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with calculated metadata."""

        total_pages = (
            (total_items + page_size - 1) // page_size if total_items > 0 else 1
        )
        start_index = (page - 1) * page_size + 1 if items else 0
        end_index = start_index + len(items) - 1 if items else 0

        pagination = PaginationMetadata(
            currentPage=page,
            pageSize=page_size,
            totalItems=total_items,
            totalPages=total_pages,
            hasNextPage=page < total_pages,
            hasPreviousPage=page > 1,
            startIndex=start_index,
            endIndex=end_index,
        )

        return cls(items=items, pagination=pagination)


class UsersPaginationRequest(PaginationRequest):
    """Specialized pagination request for users with domain-specific filters."""

    isAdmin: Optional[bool] = Field(default=None, description="Filter by admin status")
    isActive: Optional[bool] = Field(
        default=None, description="Filter by active status"
    )
    emailVerified: Optional[bool] = Field(
        default=None, description="Filter by email verification status"
    )
