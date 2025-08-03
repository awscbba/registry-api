"""
Critical Integration Tests - Tests that would have caught the production issues

These tests focus on the exact scenarios that failed in production:
1. Method name mismatches between API and service
2. Undefined person IDs in frontend
3. Non-existent API endpoints
4. Async/sync consistency
"""

import pytest
import ast
import inspect
import httpx
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

# Import the actual modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.versioned_api_handler import app
from src.services.dynamodb_service import DynamoDBService


class TestCriticalIntegration:
    """Tests that would have caught the production bugs"""

    @pytest.fixture
    def client(self):
        """Test client for the API"""
        return TestClient(app)

    @pytest.fixture
    def db_service(self):
        """Mock database service"""
        return Mock(spec=DynamoDBService)

    def test_api_service_method_consistency(self):
        """
        CRITICAL: Test that would have caught the get_person_by_id vs get_person bug
        
        This test ensures that every db_service method call in the API handler
        actually exists in the DynamoDBService class.
        """
        # Read the API handler source code
        handler_path = Path(__file__).parent.parent / "src" / "handlers" / "versioned_api_handler.py"
        with open(handler_path, 'r') as f:
            source_code = f.read()

        # Parse the AST to find all db_service method calls
        tree = ast.parse(source_code)
        
        db_service_calls = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'db_service'):
                db_service_calls.append(node.func.attr)

        # Get all actual methods from DynamoDBService
        db_service_methods = [method for method in dir(DynamoDBService) 
                             if not method.startswith('_')]

        # Check that every called method exists
        missing_methods = []
        for called_method in set(db_service_calls):
            if called_method not in db_service_methods:
                missing_methods.append(called_method)

        assert len(missing_methods) == 0, f"API calls non-existent methods: {missing_methods}"

    def test_async_sync_consistency(self):
        """
        CRITICAL: Test that would have caught async/sync mismatches
        
        This test dynamically determines which methods are async/sync
        and validates their usage in the API handler.
        """
        handler_path = Path(__file__).parent.parent / "src" / "handlers" / "versioned_api_handler.py"
        with open(handler_path, 'r') as f:
            source_code = f.read()

        # Dynamically get async/sync method signatures from DynamoDBService
        async_methods = []
        sync_methods = []
        
        for name, method in inspect.getmembers(DynamoDBService, predicate=inspect.isfunction):
            if not name.startswith('_'):
                if asyncio.iscoroutinefunction(method):
                    async_methods.append(name)
                else:
                    sync_methods.append(name)

        print(f"Detected async methods: {async_methods}")
        print(f"Detected sync methods: {sync_methods}")

        # Parse AST to find method calls and their await usage
        tree = ast.parse(source_code)
        
        method_calls = {}  # method_name -> [(line_number, has_await, line_content)]
        
        class MethodCallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_line = 1
                
            def visit_Await(self, node):
                if (isinstance(node.value, ast.Call) and
                    isinstance(node.value.func, ast.Attribute) and
                    isinstance(node.value.func.value, ast.Name) and
                    node.value.func.value.id == 'db_service'):
                    
                    method_name = node.value.func.attr
                    line_num = getattr(node, 'lineno', 0)
                    
                    if method_name not in method_calls:
                        method_calls[method_name] = []
                    method_calls[method_name].append((line_num, True, f"await db_service.{method_name}(...)"))
                
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if (isinstance(node.func, ast.Attribute) and
                    isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'db_service'):
                    
                    method_name = node.func.attr
                    line_num = getattr(node, 'lineno', 0)
                    
                    # Check if this call is not part of an await (we'll handle awaited calls separately)
                    if method_name not in method_calls:
                        method_calls[method_name] = []
                    
                    # Only add if we haven't already recorded this as an awaited call
                    existing_awaited = any(call[1] for call in method_calls[method_name] if call[0] == line_num)
                    if not existing_awaited:
                        method_calls[method_name].append((line_num, False, f"db_service.{method_name}(...)"))
                
                self.generic_visit(node)

        visitor = MethodCallVisitor()
        visitor.visit(tree)

        # Check for incorrect usage
        incorrect_usage = []
        
        for method_name, calls in method_calls.items():
            for line_num, has_await, line_content in calls:
                if method_name in async_methods and not has_await:
                    incorrect_usage.append(f"Line {line_num}: Async method '{method_name}' called without await: {line_content}")
                elif method_name in sync_methods and has_await:
                    incorrect_usage.append(f"Line {line_num}: Sync method '{method_name}' called with await: {line_content}")

        if incorrect_usage:
            print("\nIncorrect async/sync usage found:")
            for usage in incorrect_usage:
                print(f"  - {usage}")

        assert len(incorrect_usage) == 0, f"Async/sync mismatches found: {incorrect_usage}"

    @patch('src.handlers.versioned_api_handler.db_service')
    def test_person_update_workflow_integration(self, mock_db_service, client):
        """
        CRITICAL: Test the exact workflow that was failing in production
        
        This test simulates the admin dashboard person update workflow
        that was returning 404 errors.
        """
        # Mock the database responses
        mock_person = {
            "id": "test-person-id",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "postalCode": "12345"
            },
            "is_admin": False,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "is_active": True,
            "require_password_change": False,
            "last_login_at": None,
            "failed_login_attempts": 0
        }

        # Mock the get_person method (not get_person_by_id!)
        mock_db_service.get_person = AsyncMock(return_value=Mock(**mock_person))
        mock_db_service.update_person = AsyncMock(return_value=Mock(**mock_person))

        # Test GET /v2/people/{person_id} - this was failing with 404
        response = client.get("/v2/people/test-person-id")
        
        assert response.status_code == 200, f"GET person failed: {response.text}"
        
        # Verify the response format
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "version" in data
        assert data["version"] == "v2"

        # Test PUT /v2/people/{person_id} - this was also failing
        update_data = {
            "firstName": "Jane",
            "lastName": "Smith"
        }
        
        response = client.put("/v2/people/test-person-id", json=update_data)
        
        assert response.status_code == 200, f"PUT person failed: {response.text}"
        
        # Verify the update was called with correct parameters
        mock_db_service.get_person.assert_called_with("test-person-id")
        mock_db_service.update_person.assert_called_with("test-person-id", update_data)

    def test_all_v2_endpoints_exist(self, client):
        """
        CRITICAL: Test that would have caught non-existent endpoints
        
        This test verifies that all endpoints referenced in the frontend
        actually exist and return proper responses.
        """
        # Define the endpoints that the frontend expects to exist
        # Based on registry-frontend/src/config/api.ts
        expected_endpoints = [
            ("GET", "/v2/projects"),
            ("GET", "/v2/admin/projects"),
            ("GET", "/v2/admin/people"),
            ("POST", "/v2/people/check-email"),
            ("GET", "/v2/people/test-id"),  # PERSON_BY_ID
            ("PUT", "/v2/people/test-id"),  # PERSON_BY_ID
            ("DELETE", "/v2/people/test-id"),  # PERSON_BY_ID
            ("GET", "/v2/subscriptions"),
            ("POST", "/v2/subscriptions/check"),
            ("POST", "/v2/public/subscribe"),
            ("GET", "/v2/admin/subscriptions"),
            ("GET", "/v2/admin/dashboard"),
            # New subscription management endpoints
            ("GET", "/v2/projects/test-project/subscribers"),
            ("POST", "/v2/projects/test-project/subscribers"),
            ("PUT", "/v2/projects/test-project/subscribers/test-subscription"),
            ("DELETE", "/v2/projects/test-project/subscribers/test-subscription"),
        ]

        missing_endpoints = []
        
        for method, endpoint in expected_endpoints:
            try:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json={})
                elif method == "PUT":
                    response = client.put(endpoint, json={})
                elif method == "DELETE":
                    response = client.delete(endpoint)
                
                # We expect either success or a proper error (not 404 Not Found)
                if response.status_code == 404:
                    missing_endpoints.append(f"{method} {endpoint}")
                    
            except Exception as e:
                missing_endpoints.append(f"{method} {endpoint} - Exception: {str(e)}")

        assert len(missing_endpoints) == 0, f"Missing endpoints: {missing_endpoints}"

    def test_v2_response_format_consistency(self, client):
        """
        CRITICAL: Test that all v2 endpoints return consistent format
        
        This ensures that frontend response parsing works correctly.
        """
        # Test endpoints that should return v2 format
        v2_endpoints = [
            "/v2/projects",
            "/v2/subscriptions", 
            "/v2/admin/dashboard",
        ]

        format_violations = []
        
        for endpoint in v2_endpoints:
            try:
                response = client.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check v2 format: {success: true, data: ..., version: "v2"}
                    if not isinstance(data, dict):
                        format_violations.append(f"{endpoint}: Response is not a dict")
                        continue
                        
                    if "success" not in data:
                        format_violations.append(f"{endpoint}: Missing 'success' field")
                    
                    if "data" not in data:
                        format_violations.append(f"{endpoint}: Missing 'data' field")
                    
                    if "version" not in data or data["version"] != "v2":
                        format_violations.append(f"{endpoint}: Missing or incorrect 'version' field")
                        
            except Exception as e:
                format_violations.append(f"{endpoint}: Exception during test - {str(e)}")

        assert len(format_violations) == 0, f"V2 format violations: {format_violations}"

    @patch('src.handlers.versioned_api_handler.db_service')
    def test_subscription_management_crud_workflow(self, mock_db_service, client):
        """
        CRITICAL: Test the new subscription management endpoints
        
        This tests the full CRUD workflow for project subscription management
        that was previously dead code.
        """
        # Mock project exists
        mock_db_service.get_project_by_id = Mock(return_value={"id": "test-project", "name": "Test Project"})
        
        # Mock person exists
        mock_person = Mock()
        mock_person.id = "test-person"
        mock_person.first_name = "John"
        mock_person.last_name = "Doe"
        mock_person.email = "john@example.com"
        mock_db_service.get_person = AsyncMock(return_value=mock_person)
        
        # Mock subscription operations
        mock_db_service.get_all_subscriptions = AsyncMock(return_value=[])
        mock_db_service.list_people = AsyncMock(return_value=[mock_person])
        mock_db_service.create_subscription = Mock(return_value={
            "id": "test-subscription",
            "projectId": "test-project",
            "personId": "test-person",
            "status": "active",
            "createdAt": "2025-01-01T00:00:00Z"
        })
        mock_db_service.update_subscription = Mock(return_value={
            "id": "test-subscription",
            "status": "inactive"
        })
        mock_db_service.delete_subscription = Mock(return_value=True)

        # Test 1: GET subscribers for project
        response = client.get("/v2/projects/test-project/subscribers")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "subscribers" in data["data"]

        # Test 2: POST subscribe person to project
        subscribe_data = {
            "personId": "test-person",
            "status": "active",
            "notes": "Test subscription"
        }
        response = client.post("/v2/projects/test-project/subscribers", json=subscribe_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Test 3: PUT update subscription
        update_data = {"status": "inactive"}
        response = client.put("/v2/projects/test-project/subscribers/test-subscription", json=update_data)
        assert response.status_code == 200

        # Test 4: DELETE remove subscription
        response = client.delete("/v2/projects/test-project/subscribers/test-subscription")
        assert response.status_code == 200


class TestProductionHealthChecks:
    """Tests that monitor production-like scenarios"""

    @pytest.mark.integration
    def test_production_api_health(self):
        """
        Test against the actual deployed API to catch production issues
        
        This test should run against the production API to verify it's working.
        """
        api_base_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
        
        # Test critical endpoints
        critical_endpoints = [
            "/v2/projects",
            "/v2/subscriptions",
            "/v2/admin/dashboard",
        ]

        failed_endpoints = []
        
        for endpoint in critical_endpoints:
            try:
                response = httpx.get(f"{api_base_url}{endpoint}", timeout=10.0)
                if response.status_code >= 500:
                    failed_endpoints.append(f"{endpoint}: {response.status_code}")
            except Exception as e:
                failed_endpoints.append(f"{endpoint}: {str(e)}")

        # Allow some endpoints to fail with auth errors (401/403) but not 500 errors
        assert len(failed_endpoints) == 0, f"Production API health check failed: {failed_endpoints}"

    @pytest.mark.integration  
    def test_person_endpoint_exists_in_production(self):
        """
        Test the specific endpoint that was failing in production
        """
        api_base_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
        
        # Test the endpoint that was returning 404
        test_person_id = "02724257-4c6a-4aac-9c19-89c87c499bc8"
        endpoint = f"/v2/people/{test_person_id}"
        
        try:
            response = httpx.get(f"{api_base_url}{endpoint}", timeout=10.0)
            # We expect either 200 (success) or 401/403 (auth required), but NOT 404
            assert response.status_code != 404, f"Person endpoint still returns 404: {endpoint}"
        except Exception as e:
            pytest.fail(f"Failed to test person endpoint: {str(e)}")


if __name__ == "__main__":
    # Run the critical tests
    pytest.main([__file__, "-v"])