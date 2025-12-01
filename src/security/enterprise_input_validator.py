"""
Enterprise-grade context-aware input validation.
Provides different validation strategies based on endpoint context.
"""

import re
import json
import html
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, ValidationError
from datetime import datetime

from .input_validator import ValidationResult, InputValidator


class ValidationContext(str, Enum):
    """Validation context types for different endpoint categories."""

    AUTHENTICATION = "authentication"  # Login, password reset, etc.
    USER_DATA = "user_data"  # Profile updates, user creation
    CONTENT_DATA = "content_data"  # Projects, descriptions, etc.
    SYSTEM_DATA = "system_data"  # Admin operations, system config
    PUBLIC_DATA = "public_data"  # Public endpoints, subscriptions


class EnterpriseValidationResult:
    """Enhanced validation result with context information."""

    def __init__(
        self,
        is_valid: bool,
        errors: List[str] = None,
        sanitized_data: Any = None,
        context: ValidationContext = None,
        security_level: str = "standard",
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.sanitized_data = sanitized_data
        self.context = context
        self.security_level = security_level


class EnterpriseInputValidator:
    """Enterprise-grade context-aware input validator."""

    # Endpoint context mapping
    ENDPOINT_CONTEXTS = {
        # Authentication endpoints - special handling for credentials
        r"^/auth/login$": ValidationContext.AUTHENTICATION,
        r"^/auth/refresh$": ValidationContext.AUTHENTICATION,
        r"^/auth/forgot-password$": ValidationContext.AUTHENTICATION,
        r"^/auth/reset-password$": ValidationContext.AUTHENTICATION,
        r"^/auth/validate-reset-token/.*": ValidationContext.AUTHENTICATION,
        r"^/v2/public/register$": ValidationContext.AUTHENTICATION,
        # User data endpoints - moderate security
        r"^/v2/people.*": ValidationContext.USER_DATA,
        r"^/v2/admin/users.*": ValidationContext.USER_DATA,
        # Content data endpoints - standard security
        r"^/v2/projects.*": ValidationContext.CONTENT_DATA,
        r"^/v2/subscriptions.*": ValidationContext.CONTENT_DATA,
        # System/Admin endpoints - high security
        r"^/v2/admin/.*": ValidationContext.SYSTEM_DATA,
        # Public endpoints - relaxed security
        r"^/v2/public/.*": ValidationContext.PUBLIC_DATA,
    }

    # Context-specific security patterns
    AUTHENTICATION_PATTERNS = {
        # More lenient patterns for authentication - passwords can contain special chars
        "sql_injection": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\s+)",
            r"(--|#|/\*|\*/)\s*$",  # Only at end of string
            r"(\bOR\s+\d+\s*=\s*\d+\s*$)",  # Only at end
        ],
        "xss": [
            r"<script[^>]*>.*?</script>",
            r"javascript\s*:",
            r"<iframe[^>]*>.*?</iframe>",
        ],
        "nosql_injection": [
            r"\$where\s*:",
            r"\$ne\s*:",
            r"\$regex\s*:",
        ],
    }

    STANDARD_PATTERNS = {
        # Standard security patterns for general content
        "sql_injection": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\bOR\s+\w+\s*=\s*\w+)",
        ],
        "xss": [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
        ],
        "nosql_injection": [
            r"\$where",
            r"\$ne",
            r"\$gt",
            r"\$lt",
            r"\$regex",
            r"\$exists",
        ],
    }

    HIGH_SECURITY_PATTERNS = {
        # Strict patterns for admin/system endpoints
        "sql_injection": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|GRANT|REVOKE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\bOR\s+\w+\s*=\s*\w+)",
            r"(\bUNION\s+SELECT)",
        ],
        "xss": [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
        ],
        "nosql_injection": [
            r"\$where",
            r"\$ne",
            r"\$gt",
            r"\$lt",
            r"\$regex",
            r"\$exists",
            r"\$eval",
            r"\$function",
        ],
        "command_injection": [
            r"[;&|`]",
            r"\$\(",
            r"``",
        ],
    }

    @classmethod
    def _determine_context(cls, endpoint_path: str) -> ValidationContext:
        """Determine validation context based on endpoint path."""
        for pattern, context in cls.ENDPOINT_CONTEXTS.items():
            if re.match(pattern, endpoint_path):
                return context

        # Default to standard validation
        return ValidationContext.CONTENT_DATA

    @classmethod
    def _get_patterns_for_context(
        cls, context: ValidationContext
    ) -> Dict[str, List[str]]:
        """Get security patterns based on validation context."""
        if context == ValidationContext.AUTHENTICATION:
            return cls.AUTHENTICATION_PATTERNS
        elif context == ValidationContext.SYSTEM_DATA:
            return cls.HIGH_SECURITY_PATTERNS
        else:
            return cls.STANDARD_PATTERNS

    @classmethod
    def validate_request_body(
        cls,
        body_str: str,
        endpoint_path: str,
        http_method: str,
        max_length: int = 10000,
    ) -> EnterpriseValidationResult:
        """Validate request body with context awareness."""

        # Determine validation context
        context = cls._determine_context(endpoint_path)

        # Get appropriate security patterns
        patterns = cls._get_patterns_for_context(context)

        errors = []
        security_level = "standard"

        # Length validation (context-aware)
        max_len = cls._get_max_length_for_context(context, max_length)
        if len(body_str) > max_len:
            errors.append(f"Input exceeds maximum length of {max_len}")

        # Context-specific validation
        if context == ValidationContext.AUTHENTICATION:
            # Special handling for authentication requests
            validation_result = cls._validate_authentication_request(body_str, patterns)
            security_level = "authentication"
        elif context == ValidationContext.SYSTEM_DATA:
            # High security for admin endpoints
            validation_result = cls._validate_high_security_request(body_str, patterns)
            security_level = "high"
        else:
            # Standard validation for other endpoints
            validation_result = cls._validate_standard_request(body_str, patterns)
            security_level = "standard"

        if not validation_result.is_valid:
            errors.extend(validation_result.errors)

        if errors:
            return EnterpriseValidationResult(
                is_valid=False,
                errors=errors,
                context=context,
                security_level=security_level,
            )

        # Sanitize based on context
        sanitized = cls._sanitize_for_context(body_str, context)

        return EnterpriseValidationResult(
            is_valid=True,
            sanitized_data=sanitized,
            context=context,
            security_level=security_level,
        )

    @classmethod
    def _get_max_length_for_context(
        cls, context: ValidationContext, default: int
    ) -> int:
        """Get maximum length based on context."""
        context_limits = {
            ValidationContext.AUTHENTICATION: 1000,  # Credentials are typically short
            ValidationContext.USER_DATA: 5000,  # User profiles can be longer
            ValidationContext.CONTENT_DATA: 10000,  # Content can be substantial
            ValidationContext.SYSTEM_DATA: 2000,  # Admin operations should be concise
            ValidationContext.PUBLIC_DATA: 5000,  # Public data moderate length
        }
        return context_limits.get(context, default)

    @classmethod
    def _validate_authentication_request(
        cls, body_str: str, patterns: Dict[str, List[str]]
    ) -> ValidationResult:
        """Validate authentication requests with special handling for passwords."""
        try:
            # Parse JSON to validate structure
            data = json.loads(body_str)

            # Check for required authentication fields
            if not isinstance(data, dict):
                return ValidationResult(
                    False, ["Authentication data must be a JSON object"]
                )

            # Validate individual fields rather than the entire string
            # This allows passwords to contain special characters
            for field, value in data.items():
                if isinstance(value, str) and field not in [
                    "password",
                    "currentPassword",
                    "newPassword",
                    "confirmPassword",
                ]:
                    # Apply security patterns to non-password fields
                    for pattern_type, pattern_list in patterns.items():
                        for pattern in pattern_list:
                            if re.search(pattern, value, re.IGNORECASE):
                                return ValidationResult(
                                    False,
                                    [
                                        f"Field '{field}' contains potentially malicious content"
                                    ],
                                )

            return ValidationResult(True)

        except json.JSONDecodeError:
            return ValidationResult(False, ["Invalid JSON format"])

    @classmethod
    def _validate_standard_request(
        cls, body_str: str, patterns: Dict[str, List[str]]
    ) -> ValidationResult:
        """Standard validation for general requests."""
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, body_str, re.IGNORECASE):
                    return ValidationResult(
                        False,
                        [
                            f"Input contains potentially malicious content ({pattern_type})"
                        ],
                    )
        return ValidationResult(True)

    @classmethod
    def _validate_high_security_request(
        cls, body_str: str, patterns: Dict[str, List[str]]
    ) -> ValidationResult:
        """High security validation for admin/system requests."""
        # Apply all patterns with strict checking
        for pattern_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, body_str, re.IGNORECASE):
                    return ValidationResult(
                        False,
                        [
                            f"Input contains prohibited content for system operations ({pattern_type})"
                        ],
                    )

        # Additional checks for high security contexts
        try:
            data = json.loads(body_str)
            if isinstance(data, dict):
                # Check for suspicious field names
                suspicious_fields = ["eval", "exec", "system", "cmd", "shell"]
                for field in data.keys():
                    if any(sus in field.lower() for sus in suspicious_fields):
                        return ValidationResult(
                            False, [f"Suspicious field name detected: {field}"]
                        )
        except json.JSONDecodeError:
            pass  # Not JSON, continue with string validation

        return ValidationResult(True)

    @classmethod
    def _sanitize_for_context(cls, body_str: str, context: ValidationContext) -> str:
        """Sanitize input based on context."""
        if context == ValidationContext.AUTHENTICATION:
            # Minimal sanitization for auth - preserve password characters
            return body_str.strip()
        elif context == ValidationContext.SYSTEM_DATA:
            # Aggressive sanitization for admin operations
            return html.escape(body_str.strip())
        else:
            # Standard sanitization
            return html.escape(body_str.strip())

    @classmethod
    def validate_authentication_payload(
        cls, email: str, password: str
    ) -> EnterpriseValidationResult:
        """Specialized validation for authentication credentials."""
        errors = []

        # Validate email
        email_result = InputValidator.validate_email(email)
        if not email_result.is_valid:
            errors.extend([f"Email: {error}" for error in email_result.errors])

        # Validate password (basic checks only - don't restrict special characters)
        if not isinstance(password, str):
            errors.append("Password: Must be a string")
        elif len(password) < 1:
            errors.append("Password: Cannot be empty")
        elif len(password) > 128:  # Reasonable upper limit
            errors.append("Password: Too long (max 128 characters)")

        # Check for obvious injection attempts in password (very basic)
        obvious_injection_patterns = [
            r"^\s*(SELECT|INSERT|UPDATE|DELETE|DROP)\s+",
            r"<script[^>]*>",
            r"javascript\s*:",
        ]

        for pattern in obvious_injection_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                errors.append("Password: Contains invalid characters")
                break

        if errors:
            return EnterpriseValidationResult(
                is_valid=False,
                errors=errors,
                context=ValidationContext.AUTHENTICATION,
                security_level="authentication",
            )

        return EnterpriseValidationResult(
            is_valid=True,
            sanitized_data={"email": email_result.sanitized_data, "password": password},
            context=ValidationContext.AUTHENTICATION,
            security_level="authentication",
        )
