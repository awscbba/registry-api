"""
Defensive Programming Utilities

This module provides safe wrappers for common operations that frequently cause bugs:
- DateTime handling (isoformat, fromisoformat)
- Enum value extraction
- Field access and type conversion
- Database operation error handling

Usage:
    from utils.defensive_utils import safe_isoformat, safe_enum_value, safe_datetime_parse

    # Instead of: value.isoformat()
    date_string = safe_isoformat(value)

    # Instead of: enum_obj.value
    enum_string = safe_enum_value(enum_obj)

    # Instead of: datetime.fromisoformat(iso_string)
    dt_obj = safe_datetime_parse(iso_string)
"""

from datetime import datetime
from typing import Any, Optional, Union, Dict, Callable
from enum import Enum
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def safe_isoformat(value: Any, default: str = "") -> str:
    """
    Safely convert a value to ISO format string.

    Args:
        value: Any value that might be a datetime, string, or None
        default: Default value to return if conversion fails

    Returns:
        ISO format string or default value

    Examples:
        >>> safe_isoformat(datetime.now())
        '2025-08-05T01:00:00'
        >>> safe_isoformat("2025-08-05")
        '2025-08-05'
        >>> safe_isoformat(None)
        ''
    """
    if value is None:
        return default

    # If it's already a string, return as-is
    if isinstance(value, str):
        return value

    # If it has isoformat method (datetime), use it
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception as e:
            logger.warning(f"Failed to call isoformat() on {type(value)}: {e}")
            return str(value) if value else default

    # Fallback to string conversion
    return str(value) if value else default


def safe_enum_value(enum_obj: Any, default: str = "") -> str:
    """
    Safely extract the value from an enum object.

    Args:
        enum_obj: Any value that might be an enum, string, or None
        default: Default value to return if extraction fails

    Returns:
        Enum value as string or default value

    Examples:
        >>> safe_enum_value(ProjectStatus.ACTIVE)
        'active'
        >>> safe_enum_value("active")
        'active'
        >>> safe_enum_value(None)
        ''
    """
    if enum_obj is None:
        return default

    # Check if it's an enum first (before checking if it's a string)
    # This handles str-based enums like SubscriptionStatus(str, Enum)
    if (
        hasattr(enum_obj, "value")
        and hasattr(enum_obj, "__class__")
        and hasattr(enum_obj.__class__, "__bases__")
    ):
        # Check if it's actually an enum by looking for Enum in the class hierarchy
        if any("Enum" in str(base) for base in enum_obj.__class__.__mro__):
            try:
                return str(enum_obj.value)
            except Exception as e:
                logger.warning(f"Failed to get value from {type(enum_obj)}: {e}")
                return str(enum_obj) if enum_obj else default

    # If it's already a string (and not an enum), return as-is
    if isinstance(enum_obj, str):
        return enum_obj

    # Fallback to string conversion
    return str(enum_obj) if enum_obj else default


def safe_datetime_parse(
    iso_string: Any, default: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Safely parse an ISO format string to datetime.

    Args:
        iso_string: Any value that might be an ISO string, datetime, or None
        default: Default value to return if parsing fails

    Returns:
        Datetime object or default value

    Examples:
        >>> safe_datetime_parse("2025-08-05T01:00:00")
        datetime(2025, 8, 5, 1, 0)
        >>> safe_datetime_parse(datetime.now())
        datetime(2025, 8, 5, 1, 0)  # returns as-is
        >>> safe_datetime_parse(None)
        None
        >>> safe_datetime_parse("")
        None
    """
    if not iso_string:
        return default

    # If it's already a datetime, return as-is
    if isinstance(iso_string, datetime):
        return iso_string

    # If it's a string, try to parse it
    if isinstance(iso_string, str):
        try:
            return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to parse datetime from '{iso_string}': {e}")
            return default

    # Unsupported type
    logger.warning(f"Cannot parse datetime from {type(iso_string)}: {iso_string}")
    return default


def safe_field_access(obj: Any, field: str, default: Any = None) -> Any:
    """
    Safely access a field from an object with fallback options.

    Args:
        obj: Object to access field from
        field: Field name to access
        default: Default value if field doesn't exist

    Returns:
        Field value or default

    Examples:
        >>> safe_field_access(person, 'first_name', 'Unknown')
        'John'
        >>> safe_field_access(person, 'nonexistent', 'Default')
        'Default'
    """
    if obj is None:
        return default

    # Try direct attribute access
    if hasattr(obj, field):
        try:
            return getattr(obj, field, default)
        except Exception as e:
            logger.warning(f"Failed to access field '{field}' on {type(obj)}: {e}")
            return default

    # Try dictionary-style access
    if isinstance(obj, dict) and field in obj:
        return obj[field]

    # Try camelCase conversion
    camel_field = snake_to_camel(field)
    if hasattr(obj, camel_field):
        try:
            return getattr(obj, camel_field, default)
        except Exception as e:
            logger.warning(
                f"Failed to access camelCase field '{camel_field}' on {type(obj)}: {e}"
            )
            return default

    # Try snake_case conversion
    snake_field = camel_to_snake(field)
    if hasattr(obj, snake_field):
        try:
            return getattr(obj, snake_field, default)
        except Exception as e:
            logger.warning(
                f"Failed to access snake_case field '{snake_field}' on {type(obj)}: {e}"
            )
            return default

    return default


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def safe_model_dump(
    model: Any, exclude_unset: bool = True, by_alias: bool = False
) -> Dict[str, Any]:
    """
    Safely dump a Pydantic model to dictionary.

    Args:
        model: Pydantic model instance
        exclude_unset: Whether to exclude unset fields
        by_alias: Whether to use field aliases

    Returns:
        Dictionary representation of the model
    """
    if model is None:
        return {}

    if hasattr(model, "model_dump"):
        try:
            return model.model_dump(exclude_unset=exclude_unset, by_alias=by_alias)
        except Exception as e:
            logger.warning(f"Failed to dump model {type(model)}: {e}")
            return {}

    # Fallback for non-Pydantic objects
    if hasattr(model, "__dict__"):
        return model.__dict__

    return {}


def database_operation(operation_name: str):
    """
    Decorator for database operations with standardized error handling.

    Usage:
        @database_operation("update_person")
        async def update_person(self, person_id: str, data: PersonUpdate):
            # Your database operation here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.info(f"Starting database operation: {operation_name}")
                result = await func(*args, **kwargs)
                logger.info(f"Database operation completed: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Database operation failed: {operation_name} - {str(e)}")
                # Re-raise with additional context
                raise Exception(
                    f"Database operation '{operation_name}' failed: {str(e)}"
                ) from e

        return wrapper

    return decorator


def safe_update_expression_builder(
    update_data: Dict[str, Any], field_mappings: Dict[str, str] = None
) -> tuple:
    """
    Safely build DynamoDB update expressions with proper type handling.

    Args:
        update_data: Dictionary of fields to update
        field_mappings: Optional mapping of field names to DynamoDB field names

    Returns:
        Tuple of (update_expression, expression_attribute_values, expression_attribute_names)
    """
    if not update_data:
        return "", {}, {}

    update_expression = "SET updatedAt = :updated_at"
    expression_attribute_values = {":updated_at": safe_isoformat(datetime.utcnow())}
    expression_attribute_names = {}

    field_mappings = field_mappings or {}

    for field, value in update_data.items():
        if value is None:
            continue

        # Get the DynamoDB field name
        db_field = field_mappings.get(field, field)
        param_name = f":{field}"

        # Handle different value types safely
        if field.endswith("_at") or field.endswith("At") or "date" in field.lower():
            # DateTime field
            safe_value = safe_datetime_parse(value)
            if safe_value:
                expression_attribute_values[param_name] = safe_isoformat(safe_value)
        elif hasattr(value, "value"):
            # Enum field
            expression_attribute_values[param_name] = safe_enum_value(value)
        elif hasattr(value, "model_dump"):
            # Pydantic model field
            expression_attribute_values[param_name] = safe_model_dump(value)
        else:
            # Regular field
            expression_attribute_values[param_name] = value

        # Add to update expression - handle reserved words
        if db_field in ["name", "status", "location", "size", "type"]:  # Reserved words
            expression_attribute_names[f"#{field}"] = db_field
            update_expression += f", #{field} = {param_name}"
        else:
            update_expression += f", {db_field} = {param_name}"

    return update_expression, expression_attribute_values, expression_attribute_names


# Validation utilities
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> list:
    """Validate that required fields are present and not None/empty"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    return missing_fields


def sanitize_for_logging(
    data: Dict[str, Any], sensitive_fields: list = None
) -> Dict[str, Any]:
    """Remove sensitive fields from data before logging"""
    sensitive_fields = sensitive_fields or [
        "password",
        "password_hash",
        "password_salt",
        "token",
        "secret",
    ]

    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value, sensitive_fields)
        else:
            sanitized[key] = value

    return sanitized
