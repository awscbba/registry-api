"""
Router Service - Handles request routing logic following Service Registry patterns.

This service implements the routing business logic for the Lambda router function,
following established architectural patterns:
- Single Responsibility: Handles only routing logic
- Dependency Injection: Receives dependencies through constructor
- Interface Consistency: Follows same patterns as other services
- Testability: Can be easily mocked and unit tested
"""

import json
import os
from typing import Dict, Any, Optional
from src.services.logging_service import (
    EnterpriseLoggingService,
    LogLevel,
    LogCategory,
    RequestContext,
)
from src.repositories.lambda_repository import LambdaRepository
from src.utils.responses import create_error_response, create_success_response


class RouterService:
    """
    Service for handling Lambda function routing logic.

    Follows Service Registry pattern with dependency injection and single responsibility.
    """

    def __init__(
        self,
        logging_service: Optional[EnterpriseLoggingService] = None,
        lambda_repository: Optional["LambdaRepository"] = None,
    ):
        """
        Initialize router service with dependencies.

        Args:
            logging_service: Service for structured logging
            lambda_repository: Repository for Lambda function operations (injected for testability)
        """
        self.logging_service = logging_service or EnterpriseLoggingService()
        self.lambda_repository = lambda_repository or LambdaRepository(
            self.logging_service
        )

        # Load configuration from environment (following established patterns)
        self.auth_function_name = os.environ.get("AUTH_FUNCTION_NAME")
        self.api_function_name = os.environ.get("API_FUNCTION_NAME")

        self._validate_configuration()

    def route_request(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Route incoming request to appropriate Lambda function.

        Args:
            event: API Gateway event
            context: Lambda context

        Returns:
            Dict containing the response from target Lambda function
        """
        try:
            # Extract request information
            path = event.get("path", "")
            http_method = event.get("httpMethod", "GET")

            # Create request context for structured logging
            context_data = RequestContext(
                request_id=event.get("requestContext", {}).get("requestId", "unknown"),
                path=path,
                method=http_method,
                additional_data={"event_keys": list(event.keys())},
            )

            self.logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.API_ACCESS,
                message="Processing routing request",
                context=context_data,
                additional_data={
                    "path": path,
                    "method": http_method,
                    "event_keys": list(event.keys()),
                },
            )

            # Determine target function using routing rules
            target_function = self._determine_target_function(path)

            self.logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM_EVENTS,
                message="Routing decision made",
                context=context_data,
                additional_data={
                    "path": path,
                    "target_function": target_function,
                    "routing_rule": self._get_routing_rule_name(path),
                },
            )

            # Forward request to target function via repository
            return self.lambda_repository.invoke_function(
                function_name=target_function, payload=event
            )

        except Exception as e:
            error_context = RequestContext(
                request_id=event.get("requestContext", {}).get("requestId", "unknown"),
                path=event.get("path", "unknown"),
                method=event.get("httpMethod", "unknown"),
            )

            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Router service error",
                context=error_context,
                additional_data={
                    "error": str(e),
                    "path": event.get("path", "unknown"),
                    "method": event.get("httpMethod", "unknown"),
                },
            )

            return create_error_response(
                message="Routing service error",
                error_code="ROUTING_ERROR",
                status_code=500,
                details={"path": event.get("path"), "error": str(e)},
            )

    def _determine_target_function(self, path: str) -> str:
        """
        Determine target Lambda function based on request path.

        Routing Rules:
        - /auth/* -> AuthFunction (except password reset endpoints)
        - /v2/auth/* -> AuthFunction (except password reset endpoints)
        - Password reset endpoints -> API Function (has SES permissions)
        - Everything else -> API Function

        Args:
            path: Request path

        Returns:
            Target Lambda function name
        """
        # Check for password reset endpoints (route to API function for SES permissions)
        password_reset_endpoints = [
            "/forgot-password",
            "/reset-password",
            "/validate-reset-token",
        ]

        if any(endpoint in path for endpoint in password_reset_endpoints):
            return self.api_function_name

        # Route auth endpoints to auth function
        if path.startswith("/auth") or path.startswith("/v2/auth"):
            return self.auth_function_name

        # Route everything else to API function
        return self.api_function_name

    def _get_routing_rule_name(self, path: str) -> str:
        """Get human-readable routing rule name for logging."""
        password_reset_endpoints = [
            "/forgot-password",
            "/reset-password",
            "/validate-reset-token",
        ]

        if any(endpoint in path for endpoint in password_reset_endpoints):
            return "password_reset_to_api"
        elif path.startswith("/auth") or path.startswith("/v2/auth"):
            return "auth_to_auth_function"
        else:
            return "default_to_api"

    def _validate_configuration(self) -> None:
        """
        Validate required configuration is present.

        Raises:
            ValueError: If required configuration is missing
        """
        if not self.auth_function_name:
            raise ValueError("AUTH_FUNCTION_NAME environment variable is required")

        if not self.api_function_name:
            raise ValueError("API_FUNCTION_NAME environment variable is required")

        self.logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM_EVENTS,
            message="Router service configuration validated",
            additional_data={
                "auth_function": self.auth_function_name,
                "api_function": self.api_function_name,
            },
        )

    def get_routing_rules(self) -> Dict[str, Any]:
        """
        Get current routing rules for monitoring/debugging.

        Returns:
            Dict containing routing configuration
        """
        return {
            "auth_function": self.auth_function_name,
            "api_function": self.api_function_name,
            "routing_rules": {
                "password_reset": "api_function",
                "auth_endpoints": "auth_function",
                "default": "api_function",
            },
        }
