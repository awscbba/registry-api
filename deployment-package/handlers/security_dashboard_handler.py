"""
Task 19: Security Dashboard API Handler
API endpoints for admin security dashboard and monitoring
"""

import json
from typing import Dict, Any
from datetime import datetime, timedelta

from ..services.security_dashboard_service import SecurityDashboardService
from ..services.auth_service import AuthService
from ..utils.response_utils import success_response, error_response
from ..utils.auth_utils import require_admin_auth


class SecurityDashboardHandler:
    """Handler for security dashboard API endpoints"""

    def __init__(self):
        self.dashboard_service = SecurityDashboardService()
        self.auth_service = AuthService()

    @require_admin_auth
    def get_security_overview(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Get security overview for dashboard"""
        try:
            # Parse query parameters
            query_params = event.get("queryStringParameters") or {}
            days = int(query_params.get("days", 7))

            # Validate days parameter
            if days < 1 or days > 90:
                return error_response(400, "Days parameter must be between 1 and 90")

            # Get security overview
            overview = self.dashboard_service.get_security_overview(days=days)

            return success_response(
                {
                    "overview": overview,
                    "generated_at": datetime.utcnow().isoformat(),
                    "admin_dashboard": True,
                }
            )

        except ValueError as e:
            return error_response(400, f"Invalid parameter: {str(e)}")
        except Exception as e:
            return error_response(500, f"Failed to get security overview: {str(e)}")

    @require_admin_auth
    def get_security_alerts(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Get security alerts for dashboard"""
        try:
            # Parse query parameters
            query_params = event.get("queryStringParameters") or {}
            severity = query_params.get("severity", "medium")

            # Validate severity
            valid_severities = ["low", "medium", "high", "critical"]
            if severity not in valid_severities:
                return error_response(
                    400,
                    f"Invalid severity. Must be one of: {', '.join(valid_severities)}",
                )

            # Get security alerts
            alerts = self.dashboard_service.get_security_alerts(severity=severity)

            return success_response(
                {
                    "alerts": alerts,
                    "count": len(alerts),
                    "severity_filter": severity,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            return error_response(500, f"Failed to get security alerts: {str(e)}")

    @require_admin_auth
    def get_failed_login_details(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Get detailed failed login attempts"""
        try:
            # Parse query parameters
            query_params = event.get("queryStringParameters") or {}
            email = query_params.get("email")
            ip_address = query_params.get("ip")
            hours = int(query_params.get("hours", 24))

            # Validate hours parameter
            if hours < 1 or hours > 168:  # Max 1 week
                return error_response(400, "Hours parameter must be between 1 and 168")

            # Get failed login details
            failed_logins = self.dashboard_service.get_failed_login_details(
                email=email, ip_address=ip_address, hours=hours
            )

            return success_response(
                {
                    "failed_logins": failed_logins,
                    "count": len(failed_logins),
                    "filters": {
                        "email": email,
                        "ip_address": ip_address,
                        "hours": hours,
                    },
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )

        except ValueError as e:
            return error_response(400, f"Invalid parameter: {str(e)}")
        except Exception as e:
            return error_response(500, f"Failed to get failed login details: {str(e)}")

    @require_admin_auth
    def unlock_user_account(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Unlock a user account (admin action)"""
        try:
            # Parse request body
            body = json.loads(event.get("body", "{}"))
            user_id = body.get("userId")

            if not user_id:
                return error_response(400, "User ID is required")

            # Get admin email from token
            admin_email = (
                event.get("requestContext", {}).get("authorizer", {}).get("email")
            )
            if not admin_email:
                return error_response(401, "Admin authentication required")

            # Unlock account
            success = self.dashboard_service.unlock_user_account(user_id, admin_email)

            if success:
                return success_response(
                    {
                        "message": "User account unlocked successfully",
                        "user_id": user_id,
                        "unlocked_by": admin_email,
                        "unlocked_at": datetime.utcnow().isoformat(),
                    }
                )
            else:
                return error_response(500, "Failed to unlock user account")

        except json.JSONDecodeError:
            return error_response(400, "Invalid JSON in request body")
        except Exception as e:
            return error_response(500, f"Failed to unlock user account: {str(e)}")

    @require_admin_auth
    def create_security_event(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Create a security event (admin action)"""
        try:
            # Parse request body
            body = json.loads(event.get("body", "{}"))

            event_type = body.get("eventType")
            user_email = body.get("userEmail")
            ip_address = body.get("ipAddress")
            details = body.get("details", {})
            severity = body.get("severity", "medium")

            if not event_type:
                return error_response(400, "Event type is required")

            # Validate severity
            valid_severities = ["low", "medium", "high", "critical"]
            if severity not in valid_severities:
                return error_response(
                    400,
                    f"Invalid severity. Must be one of: {', '.join(valid_severities)}",
                )

            # Create security event
            success = self.dashboard_service.create_security_event(
                event_type=event_type,
                user_email=user_email,
                ip_address=ip_address,
                details=details,
                severity=severity,
            )

            if success:
                return success_response(
                    {
                        "message": "Security event created successfully",
                        "event_type": event_type,
                        "severity": severity,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
            else:
                return error_response(500, "Failed to create security event")

        except json.JSONDecodeError:
            return error_response(400, "Invalid JSON in request body")
        except Exception as e:
            return error_response(500, f"Failed to create security event: {str(e)}")

    @require_admin_auth
    def get_user_security_profile(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Get security profile for a specific user"""
        try:
            # Get user ID from path parameters
            path_params = event.get("pathParameters") or {}
            user_id = path_params.get("userId")

            if not user_id:
                return error_response(400, "User ID is required")

            # This would be implemented to get comprehensive user security info
            # For now, return placeholder structure
            user_profile = {
                "user_id": user_id,
                "security_summary": "User security profile would be implemented here",
                "recent_events": [],
                "risk_score": "low",
                "recommendations": [],
            }

            return success_response(
                {
                    "user_profile": user_profile,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            return error_response(500, f"Failed to get user security profile: {str(e)}")

    def get_dashboard_health(
        self, event: Dict[str, Any], context: Any
    ) -> Dict[str, Any]:
        """Get dashboard health status (no auth required for monitoring)"""
        try:
            health_status = {
                "status": "healthy",
                "service": "security-dashboard",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "features": {
                    "security_overview": True,
                    "failed_login_monitoring": True,
                    "password_reset_tracking": True,
                    "security_alerts": True,
                    "account_lockout_management": True,
                },
            }

            return success_response(health_status)

        except Exception as e:
            return error_response(500, f"Dashboard health check failed: {str(e)}")


# Handler instance for Lambda
security_dashboard_handler = SecurityDashboardHandler()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for security dashboard endpoints"""

    try:
        # Route based on HTTP method and path
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "/")

        # Health check
        if path == "/admin/security/health":
            return security_dashboard_handler.get_dashboard_health(event, context)

        # Security overview
        elif path == "/admin/security/overview" and http_method == "GET":
            return security_dashboard_handler.get_security_overview(event, context)

        # Security alerts
        elif path == "/admin/security/alerts" and http_method == "GET":
            return security_dashboard_handler.get_security_alerts(event, context)

        # Failed login details
        elif path == "/admin/security/failed-logins" and http_method == "GET":
            return security_dashboard_handler.get_failed_login_details(event, context)

        # Unlock user account
        elif path == "/admin/security/unlock-account" and http_method == "POST":
            return security_dashboard_handler.unlock_user_account(event, context)

        # Create security event
        elif path == "/admin/security/events" and http_method == "POST":
            return security_dashboard_handler.create_security_event(event, context)

        # User security profile
        elif path.startswith("/admin/security/users/") and http_method == "GET":
            return security_dashboard_handler.get_user_security_profile(event, context)

        else:
            return error_response(404, f"Endpoint not found: {http_method} {path}")

    except Exception as e:
        return error_response(500, f"Security dashboard error: {str(e)}")
