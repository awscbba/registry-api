"""
Simple routing Lambda that forwards requests to appropriate backend Lambda functions.
This solves the API Gateway policy size limit issue by having a single integration point.

Updated for current Service Registry architecture.
"""

import json
import boto3
import os
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Lambda client
lambda_client = boto3.client("lambda")

# Get Lambda function names from environment variables
AUTH_FUNCTION_NAME = os.environ.get("AUTH_FUNCTION_NAME")
API_FUNCTION_NAME = os.environ.get("API_FUNCTION_NAME")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Route requests to appropriate Lambda functions based on path.

    Routing rules:
    - /auth/* -> AuthFunction
    - /v2/auth/* -> AuthFunction
    - /health -> API Function (for health checks)
    - Everything else -> PeopleApiFunction
    """

    # Add logging to debug the routing
    logger.info(f"Router received event: {json.dumps(event, default=str)}")

    # Extract path from the event
    path = event.get("path", "")
    http_method = event.get("httpMethod", "GET")

    logger.info(f"Extracted path: {path}, method: {http_method}")

    # Validate environment variables
    if not AUTH_FUNCTION_NAME or not API_FUNCTION_NAME:
        error_msg = "Missing required environment variables: AUTH_FUNCTION_NAME or API_FUNCTION_NAME"
        logger.error(error_msg)
        return create_error_response(error_msg, 500)

    # Determine target function based on path
    if path.startswith("/auth") or path.startswith("/v2/auth"):
        # Special routing for password reset endpoints - route to API function (has required permissions)
        if any(
            endpoint in path
            for endpoint in [
                "/forgot-password",
                "/reset-password",
                "/validate-reset-token",
            ]
        ):
            target_function = API_FUNCTION_NAME
            logger.info(f"Routing password reset request to API function: {path}")
        else:
            # Route other auth requests to AuthFunction
            target_function = AUTH_FUNCTION_NAME
            logger.info(f"Routing auth request to AuthFunction: {path}")
    else:
        # Route all other requests (including /health, /v2/*, /) to API function
        target_function = API_FUNCTION_NAME
        logger.info(f"Routing API request to API function: {path}")

    logger.info(f"Routing to function: {target_function}")

    try:
        # Forward the request to the appropriate Lambda function
        logger.info(
            f"Invoking {target_function} with payload size: {len(json.dumps(event, default=str))}"
        )

        response = lambda_client.invoke(
            FunctionName=target_function,
            InvocationType="RequestResponse",
            Payload=json.dumps(event, default=str),
        )

        logger.info(f"Lambda response status: {response['StatusCode']}")

        # Parse the response
        payload = json.loads(response["Payload"].read())

        # Log response summary (truncated for large responses)
        response_summary = json.dumps(payload, default=str)[:200]
        logger.info(f"Parsed payload summary: {response_summary}...")

        return payload

    except Exception as e:
        # Return error response with more details
        error_msg = f"Router error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(
            error_msg,
            500,
            {"path": path, "target_function": target_function, "method": http_method},
        )


def create_error_response(
    message: str, status_code: int, extra_data: Dict = None
) -> Dict[str, Any]:
    """Create a standardized error response."""
    error_data = {
        "error": "Router internal server error",
        "message": message,
        "statusCode": status_code,
    }

    if extra_data:
        error_data.update(extra_data)

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(error_data),
    }
