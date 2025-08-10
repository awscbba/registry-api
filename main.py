"""
Main entry point for the People Registry API Lambda function.
Updated: 2025-07-29 - Deploy versioned API with v1/v2 endpoints
Updated: 2025-08-09 - Added X-Ray tracing support
"""

import logging
from mangum import Mangum

# Initialize X-Ray tracing before importing other modules
from src.utils.xray_config import XRAY_ENABLED, add_annotation, add_metadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the FastAPI app after X-Ray initialization
from src.handlers.versioned_api_handler import app

# Create Lambda handler using Mangum
_original_lambda_handler = Mangum(app)


# Wrap the lambda handler with X-Ray tracing
def traced_lambda_handler(event, context):
    """
    Lambda handler with X-Ray tracing support.
    """
    try:
        # Add X-Ray annotations for filtering
        if XRAY_ENABLED:
            add_annotation("service", "people-registry-api")
            add_annotation("version", "v2")
            add_annotation(
                "function_name", context.function_name if context else "unknown"
            )

            # Add metadata for detailed information
            add_metadata("lambda", "event_type", event.get("httpMethod", "unknown"))
            add_metadata("lambda", "path", event.get("path", "unknown"))
            add_metadata(
                "lambda", "request_id", context.aws_request_id if context else "unknown"
            )

        logger.info(
            f"Processing request: {event.get('httpMethod', 'unknown')} {event.get('path', 'unknown')}"
        )

        # Call the original handler (not the traced one!)
        response = _original_lambda_handler(event, context)

        # Add response metadata
        if XRAY_ENABLED and isinstance(response, dict):
            add_metadata("lambda", "status_code", response.get("statusCode", "unknown"))

        return response

    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        if XRAY_ENABLED:
            add_annotation("error", "true")
            add_metadata("lambda", "error", str(e))
        raise


def main():
    print("People Registry API - Versioned Lambda handler ready")
    print(f"X-Ray tracing: {'enabled' if XRAY_ENABLED else 'disabled'}")
    print("Available versions: v1 (legacy), v2 (fixed)")
    print("Available endpoints:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods)
            print(f"  {methods} {route.path}")


if __name__ == "__main__":
    main()

# Export the traced handler as the main lambda_handler
lambda_handler = traced_lambda_handler
