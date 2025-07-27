"""
Response formatting utilities to ensure consistent HTTP status codes and camelCase field naming.
This module implements the requirements for task 15.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
import uuid


class ResponseFormatter:
    """Utility class for formatting API responses with consistent structure and naming."""

    @staticmethod
    def success_response(
        data: Any,
        status_code: int = status.HTTP_200_OK,
        message: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a successful response with consistent formatting.

        Args:
            data: The response data
            status_code: HTTP status code (default: 200)
            message: Optional success message

        Returns:
            JSONResponse with formatted data
        """
        response_data = data
        if message:
            if isinstance(data, dict):
                response_data = {"message": message, **data}
            else:
                response_data = {"message": message, "data": data}

        return JSONResponse(
            content=response_data,
            status_code=status_code
        )

    @staticmethod
    def error_response(
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized error response.

        Args:
            error_code: Machine-readable error code
            message: Human-readable error message
            status_code: HTTP status code
            details: Optional list of detailed error information
            request_id: Optional request identifier

        Returns:
            HTTPException with formatted error details
        """
        error_detail = {
            "error": error_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "requestId": request_id or str(uuid.uuid4())
        }

        if details:
            error_detail["details"] = details

        return HTTPException(
            status_code=status_code,
            detail=error_detail
        )

    @staticmethod
    def validation_error_response(
        validation_errors: List[Dict[str, Any]],
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a validation error response with detailed field errors.

        Args:
            validation_errors: List of validation error details
            request_id: Optional request identifier

        Returns:
            HTTPException with validation error details
        """
        return ResponseFormatter.error_response(
            error_code="VALIDATION_ERROR",
            message="The request contains invalid data",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=validation_errors,
            request_id=request_id
        )

    @staticmethod
    def not_found_response(
        resource_type: str = "Resource",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 404 Not Found response.

        Args:
            resource_type: Type of resource that was not found
            request_id: Optional request identifier

        Returns:
            HTTPException with 404 status
        """
        return ResponseFormatter.error_response(
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            message=f"{resource_type} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id
        )

    @staticmethod
    def unauthorized_response(
        message: str = "Authentication required",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 401 Unauthorized response.

        Args:
            message: Error message
            request_id: Optional request identifier

        Returns:
            HTTPException with 401 status
        """
        return ResponseFormatter.error_response(
            error_code="AUTHENTICATION_REQUIRED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id
        )

    @staticmethod
    def forbidden_response(
        message: str = "Insufficient permissions",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 403 Forbidden response.

        Args:
            message: Error message
            request_id: Optional request identifier

        Returns:
            HTTPException with 403 status
        """
        return ResponseFormatter.error_response(
            error_code="INSUFFICIENT_PERMISSIONS",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id
        )

    @staticmethod
    def conflict_response(
        message: str,
        error_code: str = "RESOURCE_CONFLICT",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 409 Conflict response.

        Args:
            message: Error message
            error_code: Specific error code
            request_id: Optional request identifier

        Returns:
            HTTPException with 409 status
        """
        return ResponseFormatter.error_response(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            request_id=request_id
        )

    @staticmethod
    def rate_limit_response(
        message: str = "Rate limit exceeded",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 429 Too Many Requests response.

        Args:
            message: Error message
            request_id: Optional request identifier

        Returns:
            HTTPException with 429 status
        """
        return ResponseFormatter.error_response(
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            request_id=request_id
        )

    @staticmethod
    def internal_server_error_response(
        message: str = "An unexpected error occurred",
        request_id: Optional[str] = None
    ) -> HTTPException:
        """
        Create a standardized 500 Internal Server Error response.

        Args:
            message: Error message
            request_id: Optional request identifier

        Returns:
            HTTPException with 500 status
        """
        return ResponseFormatter.error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id
        )


class CamelCaseConverter:
    """Utility class for converting field names to camelCase."""

    @staticmethod
    def snake_to_camel(snake_str: str) -> str:
        """
        Convert snake_case string to camelCase.

        Args:
            snake_str: String in snake_case format

        Returns:
            String in camelCase format
        """
        components = snake_str.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])

    @staticmethod
    def convert_dict_keys(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert dictionary keys from snake_case to camelCase.

        Args:
            data: Dictionary with snake_case keys

        Returns:
            Dictionary with camelCase keys
        """
        if not isinstance(data, dict):
            return data

        converted = {}
        for key, value in data.items():
            camel_key = CamelCaseConverter.snake_to_camel(key)
            if isinstance(value, dict):
                converted[camel_key] = CamelCaseConverter.convert_dict_keys(value)
            elif isinstance(value, list):
                converted[camel_key] = [
                    CamelCaseConverter.convert_dict_keys(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                converted[camel_key] = value

        return converted

    @staticmethod
    def convert_response_data(data: Any) -> Any:
        """
        Convert response data to use camelCase field names.

        Args:
            data: Response data (dict, list, or other)

        Returns:
            Data with camelCase field names
        """
        if isinstance(data, dict):
            return CamelCaseConverter.convert_dict_keys(data)
        elif isinstance(data, list):
            return [
                CamelCaseConverter.convert_dict_keys(item) if isinstance(item, dict) else item
                for item in data
            ]
        else:
            return data


# HTTP Status Code Constants with Documentation
class HTTPStatusCodes:
    """
    HTTP status codes used throughout the API with their meanings.
    This ensures consistent status code usage across all endpoints.
    """

    # Success codes
    OK = status.HTTP_200_OK  # Successful GET requests
    CREATED = status.HTTP_201_CREATED  # Successful POST requests that create resources
    NO_CONTENT = status.HTTP_204_NO_CONTENT  # Successful DELETE requests

    # Client error codes
    BAD_REQUEST = status.HTTP_400_BAD_REQUEST  # Validation errors or malformed requests
    UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED  # Authentication required or failed
    FORBIDDEN = status.HTTP_403_FORBIDDEN  # Insufficient permissions or account locked
    NOT_FOUND = status.HTTP_404_NOT_FOUND  # Resource not found
    CONFLICT = status.HTTP_409_CONFLICT  # Resource conflicts (e.g., duplicate email)
    UNPROCESSABLE_ENTITY = status.HTTP_422_UNPROCESSABLE_ENTITY  # Semantic errors
    TOO_MANY_REQUESTS = status.HTTP_429_TOO_MANY_REQUESTS  # Rate limit exceeded

    # Server error codes
    INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR  # Unexpected server errors


# Common error codes used throughout the API
class ErrorCodes:
    """
    Standardized error codes for consistent error handling.
    """

    # Authentication errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"

    # Authorization errors
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INSUFFICIENT_PRIVILEGES = "INSUFFICIENT_PRIVILEGES"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EMAIL_FORMAT = "EMAIL_FORMAT"
    PHONE_FORMAT = "PHONE_FORMAT"
    DATE_FORMAT = "DATE_FORMAT"
    INVALID_PERSON_ID = "INVALID_PERSON_ID"
    INVALID_PAGINATION = "INVALID_PAGINATION"
    INVALID_SEARCH_PARAMETERS = "INVALID_SEARCH_PARAMETERS"

    # Resource errors
    PERSON_NOT_FOUND = "PERSON_NOT_FOUND"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Password errors
    INVALID_CURRENT_PASSWORD = "INVALID_CURRENT_PASSWORD"
    PASSWORD_POLICY_VIOLATION = "PASSWORD_POLICY_VIOLATION"
    PASSWORD_RECENTLY_USED = "PASSWORD_RECENTLY_USED"
    PASSWORD_UPDATE_FAILED = "PASSWORD_UPDATE_FAILED"

    # System errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    UPDATE_FAILED = "UPDATE_FAILED"
    DELETION_FAILED = "DELETION_FAILED"

    # Referential integrity errors
    REFERENTIAL_INTEGRITY_VIOLATION = "REFERENTIAL_INTEGRITY_VIOLATION"


# Example usage functions
def create_person_response(person_data: Dict[str, Any]) -> JSONResponse:
    """
    Example function showing how to create a properly formatted person response.

    Args:
        person_data: Person data dictionary

    Returns:
        JSONResponse with camelCase fields and 201 status
    """
    # Convert to camelCase
    camel_case_data = CamelCaseConverter.convert_response_data(person_data)

    return ResponseFormatter.success_response(
        data=camel_case_data,
        status_code=HTTPStatusCodes.CREATED
    )


def create_validation_error(field: str, message: str, code: str) -> Dict[str, Any]:
    """
    Create a validation error detail object.

    Args:
        field: Field name that failed validation
        message: Human-readable error message
        code: Machine-readable error code

    Returns:
        Validation error detail dictionary
    """
    return {
        "field": field,
        "message": message,
        "code": code
    }
