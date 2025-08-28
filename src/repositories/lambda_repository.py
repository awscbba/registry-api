"""
Lambda Repository - Handles Lambda function invocation operations.

Follows Repository pattern for abstracting Lambda service operations:
- Data Access Layer: Abstracts AWS Lambda SDK operations
- Consistent Interface: Follows same CRUD patterns as other repositories
- Testability: Can be easily mocked for testing
- Error Handling: Standardized error handling and logging
"""

import json
import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from src.services.logging_service import EnterpriseLoggingService, LogLevel, LogCategory
from src.utils.responses import create_error_response


class LambdaRepository:
    """
    Repository for Lambda function operations.

    Abstracts AWS Lambda SDK operations following Repository pattern.
    """

    def __init__(self, logging_service: EnterpriseLoggingService):
        """
        Initialize Lambda repository.

        Args:
            logging_service: Service for structured logging
        """
        self.logging_service = logging_service
        self.lambda_client = boto3.client("lambda")

    def invoke_function(
        self, function_name: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke a Lambda function with given payload.

        Args:
            function_name: Name of Lambda function to invoke
            payload: Event payload to send to function

        Returns:
            Dict containing the response from Lambda function

        Raises:
            Exception: If Lambda invocation fails
        """
        try:
            # Log invocation attempt
            payload_size = len(json.dumps(payload, default=str))
            self.logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM_EVENTS,
                message="Invoking Lambda function",
                additional_data={
                    "function_name": function_name,
                    "payload_size": payload_size,
                    "invocation_type": "RequestResponse",
                },
            )

            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload, default=str),
            )

            # Log response status
            status_code = response.get("StatusCode", 0)
            self.logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM_EVENTS,
                message="Lambda function invoked successfully",
                additional_data={
                    "function_name": function_name,
                    "status_code": status_code,
                    "response_size": len(response.get("Payload", b"").read() or b""),
                },
            )

            # Reset payload stream position for reading
            if hasattr(response["Payload"], "seek"):
                response["Payload"].seek(0)

            # Parse and return response
            payload_response = json.loads(response["Payload"].read())

            # Log response summary for debugging
            response_summary = json.dumps(payload_response, default=str)[:200]
            self.logging_service.log_structured(
                level=LogLevel.DEBUG,
                category=LogCategory.SYSTEM_EVENTS,
                message="Lambda response parsed",
                additional_data={
                    "function_name": function_name,
                    "response_summary": f"{response_summary}...",
                },
            )

            return payload_response

        except ClientError as e:
            # Handle AWS service errors
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="AWS Lambda client error",
                additional_data={
                    "function_name": function_name,
                    "error_code": error_code,
                    "error_message": error_message,
                    "aws_request_id": e.response.get("ResponseMetadata", {}).get(
                        "RequestId"
                    ),
                },
            )

            return create_error_response(
                message=f"Lambda invocation failed: {error_message}",
                error_code=f"LAMBDA_{error_code}",
                status_code=502,
                details={"function_name": function_name, "aws_error_code": error_code},
            )

        except BotoCoreError as e:
            # Handle boto3 core errors
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Boto3 core error during Lambda invocation",
                additional_data={"function_name": function_name, "error": str(e)},
            )

            return create_error_response(
                message="Lambda service unavailable",
                error_code="LAMBDA_SERVICE_ERROR",
                status_code=503,
                details={"function_name": function_name, "error": str(e)},
            )

        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Failed to parse Lambda response",
                additional_data={"function_name": function_name, "json_error": str(e)},
            )

            return create_error_response(
                message="Invalid response from target function",
                error_code="INVALID_RESPONSE",
                status_code=502,
                details={"function_name": function_name, "parse_error": str(e)},
            )

        except Exception as e:
            # Handle unexpected errors
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Unexpected error during Lambda invocation",
                additional_data={
                    "function_name": function_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            return create_error_response(
                message="Lambda invocation error",
                error_code="INVOCATION_ERROR",
                status_code=500,
                details={"function_name": function_name, "error": str(e)},
            )

    def get_function_info(self, function_name: str) -> Dict[str, Any]:
        """
        Get information about a Lambda function.

        Args:
            function_name: Name of Lambda function

        Returns:
            Dict containing function information
        """
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)

            return {
                "function_name": response["Configuration"]["FunctionName"],
                "runtime": response["Configuration"]["Runtime"],
                "handler": response["Configuration"]["Handler"],
                "last_modified": response["Configuration"]["LastModified"],
                "state": response["Configuration"]["State"],
            }

        except ClientError as e:
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Failed to get Lambda function info",
                additional_data={"function_name": function_name, "error": str(e)},
            )
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Lambda repository.

        Returns:
            Dict containing health status
        """
        try:
            # Test Lambda client connectivity
            self.lambda_client.list_functions(MaxItems=1)

            return {
                "status": "healthy",
                "service": "lambda_repository",
                "timestamp": "2025-08-28T20:00:00Z",
            }

        except Exception as e:
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message="Lambda repository health check failed",
                additional_data={"error": str(e)},
            )
            return {
                "status": "unhealthy",
                "service": "lambda_repository",
                "error": str(e),
                "timestamp": "2025-08-28T20:00:00Z",
            }
