"""
Demonstration script for the enhanced error handling and logging system.
Shows how the comprehensive error handling, structured logging, and rate limiting work together.
"""

import asyncio
from datetime import datetime
from fastapi import Request
from unittest.mock import Mock

from src.models.error_handling import (
    APIException, ErrorCode, ErrorContext, ValidationErrorDetail
)
from src.models.security_event import SecurityEventType
from src.services.logging_service import logging_service
from src.services.rate_limiting_service import rate_limiting_service, RateLimitType
from src.utils.handler_utils import (
    create_error_context, create_person_not_found_exception,
    log_authentication_with_context, log_security_event_with_context
)


async def demo_structured_logging():
    """Demonstrate structured logging capabilities."""
    print("\n=== Structured Logging Demo ===")

    # Create error context directly
    context = ErrorContext(
        request_id="demo-123",
        user_id="user-456",
        ip_address="192.168.1.100",
        user_agent="demo-client/1.0",
        path="/people/123",
        method="GET"
    )

    # Log various types of events
    await logging_service.log_structured(
        level="INFO",
        category="PERSON_OPERATIONS",
        message="Demo: Person accessed successfully",
        context=context,
        additional_data={"demo": True, "operation": "GET_PERSON"}
    )

    await logging_service.log_person_operation(
        operation="ACCESS",
        person_id="person-123",
        context=context,
        success=True,
        details={"accessed_by": "user-456", "demo": True}
    )

    print("✅ Structured logging events created successfully")


async def demo_security_event_logging():
    """Demonstrate security event logging."""
    print("\n=== Security Event Logging Demo ===")

    # Create error context directly
    context = ErrorContext(
        request_id="demo-security-123",
        ip_address="192.168.1.100",
        user_agent="demo-client/1.0",
        path="/auth/login",
        method="POST"
    )

    # Log failed login attempt
    await logging_service.log_authentication_event(
        event_type="LOGIN_FAILED",
        user_email="demo@example.com",
        context=context,
        success=False,
        failure_reason="Invalid password"
    )

    # Log security event
    event_id = await logging_service.log_security_event(
        event_type=SecurityEventType.LOGIN_FAILED,
        context=context,
        details={
            "email": "demo@example.com",
            "failure_reason": "Invalid password",
            "demo": True
        }
    )

    print(f"✅ Security event logged with ID: {event_id}")


async def demo_rate_limiting():
    """Demonstrate rate limiting functionality."""
    print("\n=== Rate Limiting Demo ===")

    # Create mock context
    context = ErrorContext(
        request_id="demo-rate-limit-123",
        ip_address="192.168.1.100",
        path="/auth/login",
        method="POST"
    )

    # Check rate limit multiple times to show progression
    for i in range(3):
        result = await rate_limiting_service.check_rate_limit(
            limit_type=RateLimitType.LOGIN_ATTEMPTS,
            identifier="192.168.1.100",
            context=context
        )

        print(f"Attempt {i+1}: Allowed={result.allowed}, Count={result.current_count}/{result.limit}")

        if not result.allowed:
            print(f"Rate limit exceeded! Retry after {result.retry_after_seconds} seconds")
            break

    print("✅ Rate limiting demonstration completed")


async def demo_error_handling():
    """Demonstrate comprehensive error handling."""
    print("\n=== Error Handling Demo ===")

    # Create error context directly
    context = ErrorContext(
        request_id="demo-error-123",
        ip_address="192.168.1.100",
        user_agent="demo-client/1.0",
        path="/people/nonexistent",
        method="GET"
    )

    try:
        # Create a person not found exception
        raise APIException(
            error_code=ErrorCode.PERSON_NOT_FOUND,
            message="Person with ID nonexistent-id not found",
            context=context
        )

    except APIException as e:
        print(f"Caught APIException:")
        print(f"  Error Code: {e.error_code}")
        print(f"  Category: {e.category}")
        print(f"  Message: {e.message}")
        print(f"  HTTP Status: {e.http_status}")

        # Convert to error response
        error_response = e.to_error_response()
        print(f"  Response: {error_response.model_dump()}")

        # Log the error
        await logging_service.log_error(e)

        print("✅ Error handled and logged successfully")


async def demo_validation_errors():
    """Demonstrate validation error handling."""
    print("\n=== Validation Error Demo ===")

    # Create error context directly
    context = ErrorContext(
        request_id="demo-validation-123",
        user_id="user-456",
        ip_address="192.168.1.100",
        user_agent="demo-client/1.0",
        path="/people",
        method="POST"
    )

    # Create validation error details
    validation_details = [
        ValidationErrorDetail(
            field="email",
            message="Invalid email format",
            code=ErrorCode.INVALID_FORMAT,
            value="invalid-email"
        ),
        ValidationErrorDetail(
            field="phone",
            message="Phone number is required",
            code=ErrorCode.REQUIRED_FIELD
        )
    ]

    try:
        # Create validation exception
        raise APIException(
            error_code=ErrorCode.INVALID_FORMAT,
            message="The request contains invalid data",
            details=validation_details,
            context=context
        )

    except APIException as e:
        print(f"Caught Validation Exception:")
        print(f"  Error Code: {e.error_code}")
        print(f"  Message: {e.message}")
        print(f"  Validation Details:")
        for detail in e.details:
            print(f"    - {detail.field}: {detail.message} ({detail.code})")

        # Log the error
        await logging_service.log_error(e)

        print("✅ Validation error handled and logged successfully")


async def demo_audit_logging():
    """Demonstrate audit logging capabilities."""
    print("\n=== Audit Logging Demo ===")

    # Create error context directly
    context = ErrorContext(
        request_id="demo-audit-123",
        user_id="user-456",
        ip_address="192.168.1.100",
        user_agent="demo-client/1.0",
        path="/people/123",
        method="PUT"
    )

    # Log audit event for person update
    before_state = {
        "email": "old@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }

    after_state = {
        "email": "new@example.com",
        "first_name": "John",
        "last_name": "Smith"
    }

    await logging_service.log_audit_event(
        action="UPDATE_PERSON",
        resource_type="person",
        resource_id="person-123",
        context=context,
        before_state=before_state,
        after_state=after_state,
        success=True
    )

    print("✅ Audit event logged successfully")
    print(f"  Action: UPDATE_PERSON")
    print(f"  Resource: person-123")
    print(f"  Changes: email, last_name")


async def main():
    """Run all demonstrations."""
    print("🚀 Enhanced Error Handling and Logging System Demo")
    print("=" * 60)

    try:
        await demo_structured_logging()
        await demo_security_event_logging()
        await demo_rate_limiting()
        await demo_error_handling()
        await demo_validation_errors()
        await demo_audit_logging()

        print("\n" + "=" * 60)
        print("✅ All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Structured logging with context")
        print("• Security event tracking")
        print("• Rate limiting with progressive penalties")
        print("• Comprehensive error handling")
        print("• Validation error details")
        print("• Audit trail logging")
        print("\nThe system provides:")
        print("• Machine-readable error codes")
        print("• Consistent error response format")
        print("• Security event correlation")
        print("• Rate limiting protection")
        print("• Comprehensive audit trails")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
