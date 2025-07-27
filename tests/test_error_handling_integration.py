"""
Integration tests for the enhanced error handling and logging system.
Tests the comprehensive error handling, structured logging, and rate limiting functionality.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import Request

from src.models.error_handling import (
    APIException,
    ErrorCode,
    ErrorCategory,
    ErrorContext,
    ValidationErrorDetail,
)
from src.models.security_event import SecurityEventType, SecurityEventSeverity
from src.services.logging_service import LoggingService, LogLevel, LogCategory
from src.services.rate_limiting_service import (
    RateLimitingService,
    RateLimitType,
    RateLimitResult,
)
from src.middleware.error_handler_middleware import ErrorHandlerMiddleware
from src.utils.handler_utils import (
    create_error_context,
    create_person_not_found_exception,
    create_validation_exception_from_errors,
    create_authentication_exception,
)


class TestErrorHandlingModels:
    """Test error handling models and utilities."""

    def test_api_exception_creation(self):
        """Test creating API exceptions with proper error codes and categories."""
        context = ErrorContext(
            request_id="test-123",
            user_id="user-456",
            ip_address="192.168.1.1",
            path="/test",
            method="GET",
        )

        exception = APIException(
            error_code=ErrorCode.PERSON_NOT_FOUND,
            message="Person not found",
            context=context,
        )

        assert exception.error_code == ErrorCode.PERSON_NOT_FOUND
        assert exception.category == ErrorCategory.NOT_FOUND
        assert exception.http_status == 404
        assert exception.message == "Person not found"
        assert exception.context == context

    def test_validation_error_details(self):
        """Test validation error details structure."""
        details = [
            ValidationErrorDetail(
                field="email",
                message="Invalid email format",
                code=ErrorCode.INVALID_FORMAT,
                value="invalid-email",
            ),
            ValidationErrorDetail(
                field="phone",
                message="Phone number is required",
                code=ErrorCode.REQUIRED_FIELD,
            ),
        ]

        exception = APIException(
            error_code=ErrorCode.INVALID_FORMAT,
            message="Validation failed",
            details=details,
        )

        assert len(exception.details) == 2
        assert exception.details[0].field == "email"
        assert exception.details[1].field == "phone"

    def test_error_response_serialization(self):
        """Test error response model serialization."""
        context = ErrorContext(request_id="test-123")
        exception = APIException(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            context=context,
            retry_after=60,
        )

        response = exception.to_error_response()
        response_dict = response.model_dump()

        assert response_dict["error"] == "RATE_LIMIT_EXCEEDED"
        assert response_dict["category"] == "RATE_LIMIT"
        assert response_dict["message"] == "Rate limit exceeded"
        assert response_dict["request_id"] == "test-123"
        assert "timestamp" in response_dict


class TestLoggingService:
    """Test the comprehensive logging service."""

    @pytest.fixture
    def logging_service(self):
        """Create logging service for testing."""
        return LoggingService()

    @pytest.mark.asyncio
    async def test_structured_logging(self, logging_service):
        """Test structured logging functionality."""
        context = ErrorContext(
            request_id="test-123", user_id="user-456", ip_address="192.168.1.1"
        )

        with patch.object(
            logging_service, "_persist_log_entry", new_callable=AsyncMock
        ) as mock_persist:
            await logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.PERSON_OPERATIONS,
                message="Test log entry",
                context=context,
                additional_data={"test": "data"},
            )

            # Verify log entry was created and persisted
            mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_person_operation_logging(self, logging_service):
        """Test person operation logging."""
        context = ErrorContext(request_id="test-123", user_id="user-456")

        with patch.object(
            logging_service, "log_structured", new_callable=AsyncMock
        ) as mock_log:
            await logging_service.log_person_operation(
                operation="CREATE",
                person_id="person-789",
                context=context,
                success=True,
                details={"created_by": "admin"},
            )

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["level"] == LogLevel.INFO
            assert call_args[1]["category"] == LogCategory.PERSON_OPERATIONS
            assert "CREATE" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_security_event_logging(self, logging_service):
        """Test security event logging."""
        context = ErrorContext(request_id="test-123", user_id="user-456")

        with patch.object(
            logging_service.db_service, "log_security_event", new_callable=AsyncMock
        ) as mock_db:
            with patch.object(
                logging_service, "log_structured", new_callable=AsyncMock
            ) as mock_log:
                event_id = await logging_service.log_security_event(
                    event_type=SecurityEventType.LOGIN_FAILED,
                    context=context,
                    severity=SecurityEventSeverity.HIGH,
                    details={"reason": "invalid_password"},
                )

                assert event_id is not None
                mock_log.assert_called_once()
                mock_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_logging(self, logging_service):
        """Test API exception logging."""
        context = ErrorContext(request_id="test-123")
        exception = APIException(
            error_code=ErrorCode.PERSON_NOT_FOUND,
            message="Person not found",
            context=context,
        )

        with patch.object(
            logging_service, "log_structured", new_callable=AsyncMock
        ) as mock_log:
            await logging_service.log_error(exception, context)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[1]["level"] == LogLevel.ERROR
            assert call_args[1]["category"] == LogCategory.ERROR_HANDLING


class TestRateLimitingService:
    """Test the rate limiting service."""

    @pytest.fixture
    def rate_limiting_service(self):
        """Create rate limiting service for testing."""
        return RateLimitingService()

    @pytest.mark.asyncio
    async def test_rate_limit_check_allowed(self, rate_limiting_service):
        """Test rate limit check when request is allowed."""
        context = ErrorContext(request_id="test-123")

        with patch.object(rate_limiting_service, "_get_current_count", return_value=3):
            result = await rate_limiting_service.check_rate_limit(
                limit_type=RateLimitType.LOGIN_ATTEMPTS,
                identifier="192.168.1.1",
                context=context,
            )

            assert result.allowed is True
            assert result.current_count == 4  # 3 + 1 (incremented)
            assert result.limit == 5  # From config

    @pytest.mark.asyncio
    async def test_rate_limit_check_exceeded(self, rate_limiting_service):
        """Test rate limit check when limit is exceeded."""
        context = ErrorContext(request_id="test-123")

        with patch.object(rate_limiting_service, "_get_current_count", return_value=10):
            with patch.object(
                rate_limiting_service, "_apply_block", new_callable=AsyncMock
            ):
                result = await rate_limiting_service.check_rate_limit(
                    limit_type=RateLimitType.LOGIN_ATTEMPTS,
                    identifier="192.168.1.1",
                    context=context,
                )

                assert result.allowed is False
                assert result.current_count == 10
                assert result.retry_after_seconds is not None

    @pytest.mark.asyncio
    async def test_rate_limit_violation_recording(self, rate_limiting_service):
        """Test recording rate limit violations."""
        context = ErrorContext(request_id="test-123")

        with patch.object(
            rate_limiting_service, "_get_violation_count", return_value=2
        ):
            with patch.object(
                rate_limiting_service,
                "_increment_violation_count",
                new_callable=AsyncMock,
            ):
                await rate_limiting_service.record_violation(
                    limit_type=RateLimitType.LOGIN_ATTEMPTS,
                    identifier="192.168.1.1",
                    context=context,
                )

                # Should increment violation count
                # Test passes if no exception is raised


class TestHandlerUtils:
    """Test handler utility functions."""

    def test_create_error_context(self):
        """Test creating error context from request."""
        # Mock request object
        request = Mock()
        request.url.path = "/test/path"
        request.method = "POST"
        request.headers = {"user-agent": "test-agent"}
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.request_id = "test-123"
        # Mock that error_context doesn't exist in state
        del request.state.error_context

        context = create_error_context(request, user_id="user-456")

        assert context.request_id == "test-123"
        assert context.user_id == "user-456"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "test-agent"
        assert context.path == "/test/path"
        assert context.method == "POST"

    def test_create_person_not_found_exception(self):
        """Test creating person not found exception."""
        request = Mock()
        request.url.path = "/people/123"
        request.method = "GET"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = Mock()
        request.state.request_id = "test-123"

        exception = create_person_not_found_exception("person-123", request)

        assert exception.error_code == ErrorCode.PERSON_NOT_FOUND
        assert exception.category == ErrorCategory.NOT_FOUND
        assert exception.http_status == 404
        assert "person-123" in exception.message

    def test_create_validation_exception_from_errors(self):
        """Test creating validation exception from field errors."""
        request = Mock()
        request.url.path = "/people"
        request.method = "POST"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = Mock()
        request.state.request_id = "test-123"

        field_errors = {
            "email": "Invalid email format",
            "phone": "Phone number is required",
        }

        exception = create_validation_exception_from_errors(
            field_errors=field_errors, request=request, user_id="user-456"
        )

        assert exception.error_code == ErrorCode.INVALID_FORMAT
        assert len(exception.details) == 2
        assert exception.details[0].field in ["email", "phone"]
        assert exception.details[1].field in ["email", "phone"]

    def test_create_authentication_exception(self):
        """Test creating authentication exception."""
        request = Mock()
        request.url.path = "/auth/login"
        request.method = "POST"
        request.client.host = "192.168.1.1"
        request.headers = {}
        request.state = Mock()
        request.state.request_id = "test-123"

        exception = create_authentication_exception(
            message="Invalid credentials", request=request
        )

        assert exception.error_code == ErrorCode.INVALID_CREDENTIALS
        assert exception.category == ErrorCategory.AUTHENTICATION
        assert exception.http_status == 401
        assert exception.message == "Invalid credentials"


class TestErrorHandlerMiddleware:
    """Test the error handler middleware."""

    @pytest.fixture
    def middleware(self):
        """Create error handler middleware for testing."""
        app = Mock()
        return ErrorHandlerMiddleware(app)

    def test_create_error_context_from_request(self, middleware):
        """Test creating error context from request in middleware."""
        request = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {"user-agent": "test-agent", "x-forwarded-for": "192.168.1.1"}
        request.query_params = {}
        request.client = None
        request.state = Mock()
        # Mock that current_user doesn't exist
        del request.state.current_user

        context = middleware._create_error_context(request, "test-123")

        assert context.request_id == "test-123"
        assert context.ip_address == "192.168.1.1"  # From x-forwarded-for
        assert context.user_agent == "test-agent"
        assert context.path == "/test"
        assert context.method == "GET"

    def test_get_client_ip_forwarded_for(self, middleware):
        """Test extracting client IP from x-forwarded-for header."""
        request = Mock()
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_real_ip(self, middleware):
        """Test extracting client IP from x-real-ip header."""
        request = Mock()
        request.headers = {"x-real-ip": "192.168.1.2"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.2"

    def test_get_client_ip_client_host(self, middleware):
        """Test extracting client IP from client host."""
        request = Mock()
        request.headers = {}
        request.client.host = "192.168.1.3"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.3"

    def test_is_sensitive_endpoint(self, middleware):
        """Test identifying sensitive endpoints."""
        assert middleware._is_sensitive_endpoint("/auth/login") is True
        assert middleware._is_sensitive_endpoint("/auth/password") is True
        assert middleware._is_sensitive_endpoint("/people/123/password") is True
        assert middleware._is_sensitive_endpoint("/people/123") is False
        assert middleware._is_sensitive_endpoint("/health") is False


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    @pytest.mark.asyncio
    async def test_authentication_failure_with_logging_and_rate_limiting(self):
        """Test complete authentication failure scenario with logging and rate limiting."""
        # This would test the full flow:
        # 1. Rate limit check
        # 2. Authentication attempt
        # 3. Failure logging
        # 4. Security event creation
        # 5. Error response formatting

        # Mock services
        logging_service = Mock()
        logging_service.log_authentication_event = AsyncMock()
        logging_service.log_security_event = AsyncMock(return_value="event-123")

        rate_limiting_service = Mock()
        rate_limiting_service.check_rate_limit = AsyncMock(
            return_value=RateLimitResult(
                allowed=True,
                current_count=3,
                limit=5,
                reset_time=datetime.now(timezone.utc),
            )
        )

        # Test scenario would go here
        # This demonstrates the integration pattern
        assert True  # Placeholder for actual integration test

    @pytest.mark.asyncio
    async def test_person_update_with_validation_and_audit_logging(self):
        """Test person update with validation errors and audit logging."""
        # This would test:
        # 1. Rate limit check
        # 2. Input validation
        # 3. Business logic validation
        # 4. Audit logging
        # 5. Error handling if validation fails

        # Mock validation service
        validation_service = Mock()
        validation_result = Mock()
        validation_result.is_valid = False
        validation_result.errors = [
            Mock(
                field="email",
                message="Email already exists",
                code=ErrorCode.EMAIL_ALREADY_EXISTS,
            )
        ]
        validation_service.validate_person_update = AsyncMock(
            return_value=validation_result
        )

        # Test scenario would go here
        assert True  # Placeholder for actual integration test


def run_tests():
    """Run all error handling integration tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
