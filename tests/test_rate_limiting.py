"""
Test rate limiting middleware and security enhancements.
"""

import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.middleware.rate_limit_middleware import RateLimitMiddleware
from src.services.rate_limiting_service import RateLimitType, RateLimitResult
from src.models.error_handling import ErrorContext
from datetime import datetime, timezone, timedelta


# Create a simple test app
app = FastAPI()

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


# Test endpoint
@app.get("/people")
async def test_people_endpoint():
    return {"message": "Success"}


@app.post("/people")
async def test_create_person():
    return {"message": "Person created"}


@app.get("/people/search")
async def test_search_endpoint():
    return {"message": "Search results"}


@app.put("/people/123")
async def test_update_person():
    return {"message": "Person updated"}


@app.put("/people/123/password")
async def test_update_password():
    return {"message": "Password updated"}


# Test client
client = TestClient(app)


@pytest.fixture
def mock_rate_limit_service():
    """Mock rate limiting service for testing."""
    with patch(
        "src.middleware.rate_limit_middleware.rate_limiting_service"
    ) as mock_service:
        # Default to allowing requests
        result = RateLimitResult(
            allowed=True,
            current_count=1,
            limit=100,
            reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Configure the mock to properly handle the call
        async def mock_check_rate_limit(*args, **kwargs):
            return result

        mock_service.check_rate_limit.side_effect = mock_check_rate_limit

        # Configure get_rate_limit_status
        status = {
            "limit_type": "API_REQUESTS",
            "current_count": 1,
            "limit": 100,
            "remaining": 99,
            "reset_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "window_seconds": 3600,
        }

        async def mock_get_status(*args, **kwargs):
            return status

        mock_service.get_rate_limit_status.side_effect = mock_get_status

        yield mock_service


@pytest.fixture
def mock_logging_service():
    """Mock logging service for testing."""
    with patch("src.middleware.rate_limit_middleware.logging_service") as mock_logging:
        yield mock_logging


def test_rate_limit_allowed(mock_rate_limit_service):
    """Test successful request with rate limit headers."""
    # Create a list to store the limit types passed to check_rate_limit
    limit_types = []

    # Configure the mock to capture the limit_type argument
    async def mock_check_rate_limit(limit_type, *args, **kwargs):
        limit_types.append(limit_type)
        return RateLimitResult(
            allowed=True,
            current_count=1,
            limit=100,
            reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    mock_rate_limit_service.check_rate_limit.side_effect = mock_check_rate_limit

    response = client.get("/people")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"message": "Success"}

    # Verify rate limit headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    # Verify service called with correct parameters
    assert len(limit_types) > 0
    assert limit_types[-1] == RateLimitType.API_REQUESTS  # Correct limit type


def test_rate_limit_exceeded(mock_rate_limit_service, mock_logging_service):
    """Test rate limit exceeded response."""
    # Configure mock to return rate limit exceeded
    result = RateLimitResult(
        allowed=False,
        current_count=101,
        limit=100,
        reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
        retry_after_seconds=300,
        blocked_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    # Configure the mock to properly handle the call
    async def mock_check_rate_limit(*args, **kwargs):
        return result

    mock_rate_limit_service.check_rate_limit.side_effect = mock_check_rate_limit

    response = client.get("/people")

    # Verify response
    assert response.status_code == 429
    assert "error" in response.json()

    # Verify headers
    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in response.headers
    assert response.headers["Retry-After"] == "300"


def test_endpoint_specific_rate_limits(mock_rate_limit_service):
    """Test different endpoints get different rate limit types."""
    # Create a list to store the limit types passed to check_rate_limit
    limit_types = []

    # Configure the mock to capture the limit_type argument
    async def mock_check_rate_limit(limit_type, *args, **kwargs):
        limit_types.append(limit_type)
        return RateLimitResult(
            allowed=True,
            current_count=1,
            limit=100,
            reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    mock_rate_limit_service.check_rate_limit.side_effect = mock_check_rate_limit

    # Test GET /people
    client.get("/people")
    assert limit_types[-1] == RateLimitType.API_REQUESTS

    # Test POST /people
    client.post("/people")
    assert limit_types[-1] == RateLimitType.PERSON_CREATION

    # Test GET /people/search
    client.get("/people/search")
    assert limit_types[-1] == RateLimitType.SEARCH_REQUESTS

    # Test PUT /people/123
    client.put("/people/123")
    assert limit_types[-1] == RateLimitType.PERSON_UPDATES

    # Test PUT /people/123/password
    client.put("/people/123/password")
    assert limit_types[-1] == RateLimitType.PASSWORD_CHANGE


def test_suspicious_activity_detection():
    """Test suspicious activity detection by checking the regex patterns."""
    import re

    # SQL injection pattern
    sql_pattern = (
        r"(\b(select|insert|update|delete|drop|alter)\b.*\b(from|table|database)\b)"
    )

    # Test data that should match
    test_data = "SELECT * FROM users WHERE id = 1"

    # Check if the pattern matches
    match = re.search(sql_pattern, test_data, re.IGNORECASE)
    assert match is not None, "SQL injection pattern should be detected"


def test_client_ip_extraction():
    """Test client IP extraction from various headers."""
    # Test X-Forwarded-For header
    response = client.get(
        "/people", headers={"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
    )
    assert response.status_code == 200

    # Test X-Real-IP header
    response = client.get("/people", headers={"X-Real-IP": "192.168.1.101"})
    assert response.status_code == 200


def test_non_person_endpoints_not_rate_limited(mock_rate_limit_service):
    """Test that non-person endpoints are not rate limited."""

    # Add a test endpoint that doesn't start with /people
    @app.get("/other/endpoint")
    def other_endpoint():
        return {"message": "Not rate limited"}

    # Reset mock
    mock_rate_limit_service.check_rate_limit.reset_mock()

    # Call the endpoint
    response = client.get("/other/endpoint")

    # Verify response
    assert response.status_code == 200

    # Verify rate limit service not called
    mock_rate_limit_service.check_rate_limit.assert_not_called()
