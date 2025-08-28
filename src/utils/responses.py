"""
Standardized API response utilities.
No field mapping needed - consistent camelCase throughout.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


def create_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"success": True, "data": data, "version": "v2"}

    if message:
        response["message"] = message

    return response


def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": {"success": False, "message": message, "version": "v2"},
    }

    if error_code:
        response["body"]["errorCode"] = error_code

    if details:
        response["body"]["details"] = details

    # For Lambda integration, body needs to be JSON string
    import json

    response["body"] = json.dumps(response["body"])

    return response


def create_list_response(
    items: List[Any], total_count: Optional[int] = None
) -> Dict[str, Any]:
    """Create a standardized list response."""
    response = {"success": True, "data": items, "count": len(items), "version": "v2"}

    if total_count is not None:
        response["totalCount"] = total_count

    return response


def create_paginated_response(
    items: List[Any], page: int, page_size: int, total_count: int
) -> Dict[str, Any]:
    """Create a standardized paginated response."""
    total_pages = (total_count + page_size - 1) // page_size

    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalCount": total_count,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrevious": page > 1,
        },
        "version": "v2",
    }
