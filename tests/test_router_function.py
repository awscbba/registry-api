"""
Tests for router_main.py routing logic.
Ensures proper routing of authentication and API requests.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock environment variables before importing router_main
with patch.dict(
    os.environ,
    {
        "AUTH_FUNCTION_NAME": "test-auth-function",
        "API_FUNCTION_NAME": "test-api-function",
    },
):
    # Add the parent directory to the path to import router_main
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import router_main


class TestRouterFunction:
    """Test router function path matching and Lambda invocation logic."""

    def setup_method(self):
        """Set up test environment variables."""
        self.auth_function_name = "test-auth-function"
        self.api_function_name = "test-api-function"

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "AUTH_FUNCTION_NAME": self.auth_function_name,
                "API_FUNCTION_NAME": self.api_function_name,
            },
        )
        self.env_patcher.start()

    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    @patch("router_main.lambda_client")
    def test_auth_path_routes_to_auth_function(self, mock_lambda_client):
        """Test that /auth/* paths route to AUTH_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"message": "success"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {
            "path": "/auth/login",
            "httpMethod": "POST",
            "body": json.dumps({"email": "test@example.com", "password": "test123"}),
        }

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.auth_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 200

    @patch("router_main.lambda_client")
    def test_v2_auth_path_routes_to_auth_function(self, mock_lambda_client):
        """Test that /v2/auth/* paths route to AUTH_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"message": "success"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {
            "path": "/v2/auth/login",
            "httpMethod": "POST",
            "body": json.dumps({"email": "test@example.com", "password": "test123"}),
        }

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.auth_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 200

    @patch("router_main.lambda_client")
    def test_auth_register_path_routes_to_auth_function(self, mock_lambda_client):
        """Test that /auth/register paths route to AUTH_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 201, "body": json.dumps({"message": "user created"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {
            "path": "/auth/register",
            "httpMethod": "POST",
            "body": json.dumps({"email": "new@example.com", "password": "newpass123"}),
        }

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.auth_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 201

    @patch("router_main.lambda_client")
    def test_v2_auth_register_path_routes_to_auth_function(self, mock_lambda_client):
        """Test that /v2/auth/register paths route to AUTH_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 201, "body": json.dumps({"message": "user created"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {
            "path": "/v2/auth/register",
            "httpMethod": "POST",
            "body": json.dumps({"email": "new@example.com", "password": "newpass123"}),
        }

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.auth_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 201

    @patch("router_main.lambda_client")
    def test_api_path_routes_to_api_function(self, mock_lambda_client):
        """Test that non-auth paths route to API_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"data": []})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {"path": "/v2/projects", "httpMethod": "GET"}

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.api_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 200

    @patch("router_main.lambda_client")
    def test_health_path_routes_to_api_function(self, mock_lambda_client):
        """Test that /health path routes to API_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"status": "healthy"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {"path": "/health", "httpMethod": "GET"}

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.api_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 200

    @patch("router_main.lambda_client")
    def test_v2_subscriptions_path_routes_to_api_function(self, mock_lambda_client):
        """Test that /v2/subscriptions path routes to API_FUNCTION_NAME."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"data": []})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {"path": "/v2/subscriptions", "httpMethod": "GET"}

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName=self.api_function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(event),
        )
        assert result["statusCode"] == 200

    @patch("router_main.lambda_client")
    def test_router_handles_lambda_invocation_error(self, mock_lambda_client):
        """Test that router handles Lambda invocation errors gracefully."""
        # Arrange
        mock_lambda_client.invoke.side_effect = Exception("Lambda invocation failed")

        event = {"path": "/auth/login", "httpMethod": "POST"}

        # Act
        result = router_main.lambda_handler(event, {})

        # Assert
        assert result["statusCode"] == 500
        assert "Router internal server error" in json.loads(result["body"])["error"]
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"

    @patch("router_main.lambda_client")
    def test_router_logs_routing_decisions(self, mock_lambda_client):
        """Test that router logs routing decisions for debugging."""
        # Arrange
        mock_response = {"StatusCode": 200, "Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {"statusCode": 200, "body": json.dumps({"message": "success"})}
        ).encode()
        mock_lambda_client.invoke.return_value = mock_response

        event = {"path": "/v2/auth/login", "httpMethod": "POST"}

        # Act
        with patch("router_main.logger") as mock_logger:
            router_main.lambda_handler(event, {})

            # Assert logging calls
            mock_logger.info.assert_any_call(
                f"Router received event: {json.dumps(event)}"
            )
            mock_logger.info.assert_any_call(
                "Extracted path: /v2/auth/login, method: POST"
            )
            mock_logger.info.assert_any_call(
                "Routing auth request to AuthFunction: /v2/auth/login"
            )
            mock_logger.info.assert_any_call(
                f"Routing to function: {self.auth_function_name}"
            )

    def test_edge_case_empty_path(self):
        """Test router behavior with empty path."""
        # Arrange
        event = {"path": "", "httpMethod": "GET"}

        # Act & Assert - Should not crash and should route to API function
        with patch("router_main.lambda_client") as mock_lambda_client:
            mock_response = {"StatusCode": 200, "Payload": MagicMock()}
            mock_response["Payload"].read.return_value = json.dumps(
                {"statusCode": 200, "body": json.dumps({"message": "success"})}
            ).encode()
            mock_lambda_client.invoke.return_value = mock_response

            result = router_main.lambda_handler(event, {})

            # Should route to API function (not auth)
            mock_lambda_client.invoke.assert_called_once_with(
                FunctionName=self.api_function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(event),
            )

    def test_edge_case_missing_path(self):
        """Test router behavior with missing path key."""
        # Arrange
        event = {"httpMethod": "GET"}

        # Act & Assert - Should not crash and should route to API function
        with patch("router_main.lambda_client") as mock_lambda_client:
            mock_response = {"StatusCode": 200, "Payload": MagicMock()}
            mock_response["Payload"].read.return_value = json.dumps(
                {"statusCode": 200, "body": json.dumps({"message": "success"})}
            ).encode()
            mock_lambda_client.invoke.return_value = mock_response

            result = router_main.lambda_handler(event, {})

            # Should route to API function (not auth)
            mock_lambda_client.invoke.assert_called_once_with(
                FunctionName=self.api_function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(event),
            )


if __name__ == "__main__":
    pytest.main([__file__])
