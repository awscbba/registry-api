"""
Enterprise-grade input validation and sanitization.
"""

import re
import html
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ValidationError
from datetime import datetime


class ValidationResult:
    """Result of input validation."""

    def __init__(
        self, is_valid: bool, errors: List[str] = None, sanitized_data: Any = None
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.sanitized_data = sanitized_data


class InputValidator:
    """Enterprise-grade input validation and sanitization."""

    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bOR\s+\w+\s*=\s*\w+)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
    ]

    NOSQL_INJECTION_PATTERNS = [
        r"\$where",
        r"\$ne",
        r"\$gt",
        r"\$lt",
        r"\$regex",
        r"\$exists",
    ]

    @classmethod
    def validate_and_sanitize_string(
        cls, value: str, max_length: int = 1000
    ) -> ValidationResult:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            return ValidationResult(False, ["Input must be a string"])

        errors = []

        # Length validation
        if len(value) > max_length:
            errors.append(f"Input exceeds maximum length of {max_length}")

        # Security validation
        for pattern in (
            cls.SQL_INJECTION_PATTERNS + cls.XSS_PATTERNS + cls.NOSQL_INJECTION_PATTERNS
        ):
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Input contains potentially malicious content")
                break

        if errors:
            return ValidationResult(False, errors)

        # Sanitize
        sanitized = html.escape(value.strip())
        return ValidationResult(True, sanitized_data=sanitized)

    @classmethod
    def validate_email(cls, email: str) -> ValidationResult:
        """Validate email format."""
        if not isinstance(email, str):
            return ValidationResult(False, ["Email must be a string"])

        # Basic email regex (more comprehensive than simple validation)
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            return ValidationResult(False, ["Invalid email format"])

        if len(email) > 254:  # RFC 5321 limit
            return ValidationResult(False, ["Email address too long"])

        return ValidationResult(True, sanitized_data=email.lower().strip())

    @classmethod
    def validate_id(cls, id_value: str) -> ValidationResult:
        """Validate ID format (UUID)."""
        if not isinstance(id_value, str):
            return ValidationResult(False, ["ID must be a string"])

        # UUID pattern
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

        if not re.match(uuid_pattern, id_value, re.IGNORECASE):
            return ValidationResult(False, ["Invalid ID format"])

        return ValidationResult(True, sanitized_data=id_value.lower())

    @classmethod
    def validate_phone(cls, phone: str) -> ValidationResult:
        """Validate phone number."""
        if not isinstance(phone, str):
            return ValidationResult(False, ["Phone must be a string"])

        # Remove common formatting
        cleaned_phone = re.sub(r"[^\d+]", "", phone)

        # Basic phone validation (international format)
        if not re.match(r"^\+?[1-9]\d{1,14}$", cleaned_phone):
            return ValidationResult(False, ["Invalid phone number format"])

        return ValidationResult(True, sanitized_data=cleaned_phone)

    @classmethod
    def validate_date(cls, date_str: str) -> ValidationResult:
        """Validate date format (YYYY-MM-DD)."""
        if not isinstance(date_str, str):
            return ValidationResult(False, ["Date must be a string"])

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return ValidationResult(True, sanitized_data=date_str)
        except ValueError:
            return ValidationResult(False, ["Invalid date format. Use YYYY-MM-DD"])

    @classmethod
    def validate_model_data(
        cls, model_class: BaseModel, data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against Pydantic model."""
        try:
            validated_model = model_class(**data)
            return ValidationResult(True, sanitized_data=validated_model.model_dump())
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return ValidationResult(False, errors)

    @classmethod
    def sanitize_dict(
        cls, data: Dict[str, Any], allowed_keys: List[str] = None
    ) -> Dict[str, Any]:
        """Sanitize dictionary data."""
        if not isinstance(data, dict):
            return {}

        sanitized = {}

        for key, value in data.items():
            # Check allowed keys
            if allowed_keys and key not in allowed_keys:
                continue

            # Sanitize key
            if isinstance(key, str):
                key_result = cls.validate_and_sanitize_string(key, max_length=100)
                if not key_result.is_valid:
                    continue
                key = key_result.sanitized_data

            # Sanitize value
            if isinstance(value, str):
                value_result = cls.validate_and_sanitize_string(value)
                if value_result.is_valid:
                    sanitized[key] = value_result.sanitized_data
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                    if not isinstance(item, str)
                    or cls.validate_and_sanitize_string(item).is_valid
                ]

        return sanitized


class SecurityValidator:
    """Additional security validations."""

    @staticmethod
    def validate_user_permissions(user_id: str, resource_id: str, action: str) -> bool:
        """Validate user permissions for resource access."""
        # TODO: Implement proper RBAC
        # This is a placeholder for enterprise permission system
        return True

    @staticmethod
    def validate_rate_limit(user_id: str, endpoint: str) -> bool:
        """Validate rate limiting."""
        # TODO: Implement proper rate limiting
        # This is a placeholder for enterprise rate limiting
        return True

    @staticmethod
    def log_security_event(event_type: str, user_id: str, details: Dict[str, Any]):
        """Log security events for monitoring."""
        # TODO: Implement proper security logging
        # This should integrate with enterprise SIEM systems
        pass
