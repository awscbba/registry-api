"""
Router Lambda entry point following Service Registry architecture patterns.
This solves the API Gateway policy size limit issue by having a single integration point.

Follows established architectural patterns:
- Service Registry pattern for business logic
- Repository pattern for data access (if needed)
- Dependency injection for services
- Standardized error handling
"""

from typing import Dict, Any
from src.services.router_service import RouterService
from src.services.logging_service import EnterpriseLoggingService, LogLevel, LogCategory
from src.utils.responses import create_error_response


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entry point for router function.

    Follows Service Registry pattern - delegates to RouterService for business logic.
    """

    # Initialize logging service following established patterns
    logging_service = EnterpriseLoggingService()

    try:
        # Initialize router service following Service Registry pattern
        router_service = RouterService(logging_service=logging_service)

        # Delegate routing logic to service layer
        return router_service.route_request(event, context)

    except Exception as e:
        # Standardized error handling following established patterns
        logging_service.log_structured(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR_HANDLING,
            message="Router Lambda handler error",
            additional_data={"error": str(e)},
        )

        return create_error_response(
            message="Router service unavailable",
            error_code="ROUTER_ERROR",
            status_code=500,
            details={"error": str(e)},
        )
