"""
Tests for RouterService following established testing patterns.

Tests the Service Registry pattern implementation for router functionality.
"""

import pytest
from unittest.mock import Mock, patch
from src.services.router_service import RouterService
from src.services.logging_service import EnterpriseLoggingService
from src.repositories.lambda_repository import LambdaRepository


class TestRouterService:
    """Test RouterService following established testing patterns."""

    def setup_method(self):
        """Set up test dependencies following dependency injection patterns."""
        self.logging_service = EnterpriseLoggingService()
        self.mock_lambda_repository = Mock(spec=LambdaRepository)

        # Mock environment variables
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "AUTH_FUNCTION_NAME": "test-auth-function",
                "API_FUNCTION_NAME": "test-api-function",
            },
        )
        self.env_patcher.start()

        self.router_service = RouterService(
            logging_service=self.logging_service,
            lambda_repository=self.mock_lambda_repository,
        )

    def teardown_method(self):
        """Clean up test environment."""
        self.env_patcher.stop()

    def test_route_auth_endpoint_to_auth_function(self):
        """Test that auth endpoints route to auth function."""
        # Arrange
        event = {"path": "/auth/login", "httpMethod": "POST"}
        context = Mock()
        expected_response = {"statusCode": 200, "body": "success"}
        self.mock_lambda_repository.invoke_function.return_value = expected_response

        # Act
        result = self.router_service.route_request(event, context)

        # Assert
        self.mock_lambda_repository.invoke_function.assert_called_once_with(
            function_name="test-auth-function", payload=event
        )
        assert result == expected_response

    def test_route_v2_auth_endpoint_to_auth_function(self):
        """Test that v2 auth endpoints route to auth function."""
        # Arrange
        event = {"path": "/v2/auth/refresh", "httpMethod": "POST"}
        context = Mock()
        expected_response = {"statusCode": 200, "body": "success"}
        self.mock_lambda_repository.invoke_function.return_value = expected_response

        # Act
        result = self.router_service.route_request(event, context)

        # Assert
        self.mock_lambda_repository.invoke_function.assert_called_once_with(
            function_name="test-auth-function", payload=event
        )
        assert result == expected_response

    def test_route_password_reset_to_api_function(self):
        """Test that password reset endpoints route to API function (for SES permissions)."""
        # Arrange
        password_reset_paths = [
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/validate-reset-token",
        ]

        for path in password_reset_paths:
            event = {"path": path, "httpMethod": "POST"}
            context = Mock()
            expected_response = {"statusCode": 200, "body": "success"}
            self.mock_lambda_repository.invoke_function.return_value = expected_response

            # Act
            result = self.router_service.route_request(event, context)

            # Assert
            self.mock_lambda_repository.invoke_function.assert_called_with(
                function_name="test-api-function", payload=event
            )
            assert result == expected_response

    def test_route_api_endpoints_to_api_function(self):
        """Test that non-auth endpoints route to API function."""
        # Arrange
        api_paths = ["/v2/people", "/v2/projects", "/health", "/subscriptions"]

        for path in api_paths:
            event = {"path": path, "httpMethod": "GET"}
            context = Mock()
            expected_response = {"statusCode": 200, "body": "success"}
            self.mock_lambda_repository.invoke_function.return_value = expected_response

            # Act
            result = self.router_service.route_request(event, context)

            # Assert
            self.mock_lambda_repository.invoke_function.assert_called_with(
                function_name="test-api-function", payload=event
            )
            assert result == expected_response

    def test_routing_rules_configuration(self):
        """Test that routing rules are properly configured."""
        # Act
        rules = self.router_service.get_routing_rules()

        # Assert
        assert rules["auth_function"] == "test-auth-function"
        assert rules["api_function"] == "test-api-function"
        assert rules["routing_rules"]["password_reset"] == "api_function"
        assert rules["routing_rules"]["auth_endpoints"] == "auth_function"
        assert rules["routing_rules"]["default"] == "api_function"

    def test_configuration_validation_missing_auth_function(self):
        """Test that missing AUTH_FUNCTION_NAME raises ValueError."""
        with patch.dict("os.environ", {"API_FUNCTION_NAME": "test-api"}, clear=True):
            with pytest.raises(
                ValueError, match="AUTH_FUNCTION_NAME environment variable is required"
            ):
                RouterService(logging_service=self.logging_service)

    def test_configuration_validation_missing_api_function(self):
        """Test that missing API_FUNCTION_NAME raises ValueError."""
        with patch.dict("os.environ", {"AUTH_FUNCTION_NAME": "test-auth"}, clear=True):
            with pytest.raises(
                ValueError, match="API_FUNCTION_NAME environment variable is required"
            ):
                RouterService(logging_service=self.logging_service)

    def test_error_handling_in_route_request(self):
        """Test error handling when Lambda repository fails."""
        # Arrange
        event = {"path": "/v2/people", "httpMethod": "GET"}
        context = Mock()
        self.mock_lambda_repository.invoke_function.side_effect = Exception(
            "Lambda error"
        )

        # Act
        result = self.router_service.route_request(event, context)

        # Assert
        assert result["statusCode"] == 500
        assert "Routing service error" in result["body"]
        assert "ROUTING_ERROR" in result["body"]

    def test_determine_target_function_logic(self):
        """Test the internal routing logic."""
        # Test auth endpoints
        assert (
            self.router_service._determine_target_function("/auth/login")
            == "test-auth-function"
        )
        assert (
            self.router_service._determine_target_function("/v2/auth/refresh")
            == "test-auth-function"
        )

        # Test password reset endpoints (should go to API function)
        assert (
            self.router_service._determine_target_function("/auth/forgot-password")
            == "test-api-function"
        )
        assert (
            self.router_service._determine_target_function("/auth/reset-password")
            == "test-api-function"
        )

        # Test API endpoints
        assert (
            self.router_service._determine_target_function("/v2/people")
            == "test-api-function"
        )
        assert (
            self.router_service._determine_target_function("/health")
            == "test-api-function"
        )

    def test_routing_rule_names(self):
        """Test routing rule name generation for logging."""
        assert (
            self.router_service._get_routing_rule_name("/auth/forgot-password")
            == "password_reset_to_api"
        )
        assert (
            self.router_service._get_routing_rule_name("/auth/login")
            == "auth_to_auth_function"
        )
        assert (
            self.router_service._get_routing_rule_name("/v2/people") == "default_to_api"
        )
