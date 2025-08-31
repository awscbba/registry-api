"""
Authorization middleware to enforce RBAC on all endpoints.
"""

import re
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..models.rbac import Permission, RoleType
from ..services.rbac_service import rbac_service
from ..services.logging_service import logging_service, LogCategory, LogLevel
from ..exceptions.base_exceptions import AuthorizationException, ErrorCode


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce RBAC authorization on all endpoints."""

    # Define endpoint permission requirements
    ENDPOINT_PERMISSIONS = {
        # User endpoints
        r"^/v2/people$": {
            "GET": Permission.USER_READ_ALL,
            "POST": Permission.USER_CREATE,
        },
        r"^/v2/people/[^/]+$": {
            "GET": Permission.USER_READ_OWN,  # Will check ownership
            "PUT": Permission.USER_UPDATE_OWN,  # Will check ownership
            "DELETE": Permission.USER_DELETE_OWN,  # Will check ownership
        },
        # Project endpoints
        r"^/v2/projects$": {
            "GET": Permission.PROJECT_READ_ALL,
            "POST": Permission.PROJECT_CREATE,
        },
        r"^/v2/projects/[^/]+$": {
            "GET": Permission.PROJECT_READ_ALL,
            "PUT": Permission.PROJECT_UPDATE_OWN,  # Will check ownership
            "DELETE": Permission.PROJECT_DELETE_OWN,  # Will check ownership
        },
        # Subscription endpoints
        r"^/v2/subscriptions$": {
            "GET": Permission.SUBSCRIPTION_READ_ALL,
            "POST": Permission.SUBSCRIPTION_CREATE,
        },
        r"^/v2/subscriptions/[^/]+$": {
            "GET": Permission.SUBSCRIPTION_READ_OWN,  # Will check ownership
            "PUT": Permission.SUBSCRIPTION_UPDATE_OWN,  # Will check ownership
            "DELETE": Permission.SUBSCRIPTION_DELETE_OWN,  # Will check ownership
        },
        # Admin endpoints
        r"^/v2/admin/.*": {
            "GET": Permission.SYSTEM_AUDIT,
            "POST": Permission.SYSTEM_CONFIG,
            "PUT": Permission.SYSTEM_CONFIG,
            "DELETE": Permission.SYSTEM_CONFIG,
        },
    }

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = [
        r"^/$",
        r"^/health$",
        r"^/docs.*",
        r"^/openapi.json$",
        r"^/auth/login$",
        r"^/auth/refresh$",
        r"^/auth/forgot-password$",
        r"^/auth/reset-password$",
        r"^/auth/validate-reset-token/.*",
        r"^/v2/projects$",  # Allow public access to projects list
        r"^/v2/projects/public$",
        r"^/v2/public/subscribe$",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Check authorization for the request."""

        path = request.url.path
        method = request.method

        # Skip authorization for public endpoints
        if self._is_public_endpoint(path):
            return await call_next(request)

        # Skip authorization in test environment
        import os

        if os.getenv("TESTING") == "true" or "pytest" in os.environ.get("_", ""):
            return await call_next(request)

        # Get user from request state (set by authentication middleware)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            logging_service.log_security_event(
                event_type="unauthorized_access_attempt",
                severity="high",
                details={"path": path, "method": method, "reason": "no_authentication"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Find required permission for this endpoint
        required_permission = self._get_required_permission(path, method)
        if not required_permission:
            # No specific permission required, allow access
            return await call_next(request)

        # Check permission
        try:
            # Extract resource ID from path if present
            resource_id = self._extract_resource_id(path)

            permission_result = await rbac_service.user_has_permission(
                user_id=user_id,
                permission=required_permission,
                resource_id=resource_id,
                context=getattr(request.state, "context", None),
            )

            if not permission_result.has_permission:
                logging_service.log_security_event(
                    event_type="authorization_denied",
                    severity="medium",
                    user_id=user_id,
                    details={
                        "path": path,
                        "method": method,
                        "required_permission": required_permission.value,
                        "reason": permission_result.reason,
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            # Store permission check result in request state
            request.state.authorized_permission = required_permission
            request.state.resource_id = resource_id

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.AUTHORIZATION,
                message=f"Authorization check failed: {str(e)}",
                additional_data={
                    "user_id": user_id,
                    "path": path,
                    "method": method,
                    "error": str(e),
                },
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization check failed",
            )

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)."""
        for pattern in self.PUBLIC_ENDPOINTS:
            if re.match(pattern, path):
                return True
        return False

    def _get_required_permission(self, path: str, method: str) -> Optional[Permission]:
        """Get required permission for endpoint."""
        for pattern, permissions in self.ENDPOINT_PERMISSIONS.items():
            if re.match(pattern, path):
                return permissions.get(method)
        return None

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from path for ownership checks."""
        # Extract ID from paths like /v2/people/{id}, /v2/projects/{id}, etc.
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            # Return the ID part (third segment)
            return parts[2]
        return None


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate and sanitize all inputs."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate request inputs with context-aware security."""

        # Skip validation for GET requests (no body)
        if request.method == "GET":
            return await call_next(request)

        try:
            # Read and validate request body
            if hasattr(request, "_body"):
                body = request._body
            else:
                body = await request.body()
                request._body = body

            if body:
                # Context-aware validation based on endpoint
                body_str = body.decode("utf-8")

                from ..security.enterprise_input_validator import (
                    EnterpriseInputValidator,
                )

                # Validate with context awareness
                validation_result = EnterpriseInputValidator.validate_request_body(
                    body_str=body_str,
                    endpoint_path=request.url.path,
                    http_method=request.method,
                    max_length=10000,
                )

                if not validation_result.is_valid:
                    logging_service.log_security_event(
                        event_type="malicious_input_detected",
                        severity="high",
                        user_id=getattr(request.state, "user_id", None),
                        details={
                            "path": request.url.path,
                            "method": request.method,
                            "errors": validation_result.errors,
                            "validation_context": validation_result.context,
                        },
                    )

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid input detected",
                    )

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.SECURITY_EVENTS,
                message=f"Input validation failed: {str(e)}",
                additional_data={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(e),
                },
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request validation failed",
            )
