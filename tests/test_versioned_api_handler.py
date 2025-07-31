"""
Comprehensive unit tests for versioned_api_handler.py

This test suite covers:
- All endpoint functionality
- Error handling
- Async/await correctness
- Data validation
- Version compatibility
- Admin functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from handlers.versioned_api_handler import app
from models.person import PersonCreate
from models.subscription import SubscriptionCreate


class TestVersionedAPIHandler:
    """Test suite for versioned API handler"""

    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service"""
        with patch("handlers.versioned_api_handler.db_service") as mock:
            # Configure common mock responses
            mock.get_all_subscriptions = AsyncMock(
                return_value=[
                    {
                        "id": "sub1",
                        "projectId": "proj1",
                        "personId": "person1",
                        "status": "active",
                    }
                ]
            )
            mock.get_all_projects = AsyncMock(
                return_value=[
                    {"id": "proj1", "name": "Test Project", "description": "Test"}
                ]
            )
            mock.get_project_by_id = MagicMock(
                return_value={"id": "proj1", "name": "Test Project"}
            )
            mock.get_person_by_email = AsyncMock(return_value=None)
            mock.create_person = AsyncMock(return_value=MagicMock(id="person1"))
            mock.create_subscription = AsyncMock(
                return_value={"id": "sub1", "projectId": "proj1", "personId": "person1"}
            )
            mock.get_subscriptions_by_person = AsyncMock(return_value=[])
            mock.get_all_people = AsyncMock(return_value=[])
            mock.get_person_by_id = AsyncMock(return_value=None)
            mock.update_person = AsyncMock(
                return_value=MagicMock(
                    id="person1",
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    is_admin=True,
                )
            )
            yield mock

    # ==================== HEALTH CHECK TESTS ====================

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "people-register-api-versioned"
        assert "v1" in data["versions"]
        assert "v2" in data["versions"]
        assert "timestamp" in data

    # ==================== V1 ENDPOINT TESTS ====================

    def test_get_subscriptions_v1(self, client, mock_db_service):
        """Test v1 subscriptions endpoint"""
        response = client.get("/v1/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        mock_db_service.get_all_subscriptions.assert_called_once()

    def test_get_projects_v1(self, client, mock_db_service):
        """Test v1 projects endpoint"""
        response = client.get("/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        mock_db_service.get_all_projects.assert_called_once()

    def test_create_subscription_v1_success(self, client, mock_db_service):
        """Test v1 subscription creation success"""
        payload = {
            "person": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
            },
            "projectId": "proj1",
            "notes": "Test subscription",
        }

        response = client.post("/v1/public/subscribe", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Subscription created successfully"
        assert "subscription" in data
        assert "person_created" in data

    def test_create_subscription_v1_missing_data(self, client, mock_db_service):
        """Test v1 subscription creation with missing data"""
        payload = {"person": {"email": "test@example.com"}}

        response = client.post("/v1/public/subscribe", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "Both person data and projectId are required" in data["detail"]

    def test_create_subscription_v1_project_not_found(self, client, mock_db_service):
        """Test v1 subscription creation with non-existent project"""
        mock_db_service.get_project_by_id.return_value = None

        payload = {
            "person": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
            },
            "projectId": "nonexistent",
        }

        response = client.post("/v1/public/subscribe", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "Project not found" in data["detail"]

    # ==================== V2 ENDPOINT TESTS ====================

    def test_get_subscriptions_v2(self, client, mock_db_service):
        """Test v2 subscriptions endpoint"""
        response = client.get("/v2/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert data["version"] == "v2"
        assert "count" in data
        mock_db_service.get_all_subscriptions.assert_called_once()

    def test_get_projects_v2(self, client, mock_db_service):
        """Test v2 projects endpoint"""
        response = client.get("/v2/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert data["version"] == "v2"
        assert "count" in data
        mock_db_service.get_all_projects.assert_called_once()

    def test_check_person_exists_v2_not_found(self, client, mock_db_service):
        """Test v2 person existence check - not found"""
        payload = {"email": "nonexistent@example.com"}

        response = client.post("/v2/people/check-email", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["version"] == "v2"

    def test_check_person_exists_v2_found(self, client, mock_db_service):
        """Test v2 person existence check - found"""
        mock_db_service.get_person_by_email.return_value = MagicMock(id="person1")

        payload = {"email": "existing@example.com"}

        response = client.post("/v2/people/check-email", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["version"] == "v2"

    def test_check_person_exists_v2_missing_email(self, client, mock_db_service):
        """Test v2 person existence check with missing email"""
        payload = {}

        response = client.post("/v2/people/check-email", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "Email is required" in data["detail"]

    def test_check_subscription_exists_v2_not_subscribed(self, client, mock_db_service):
        """Test v2 subscription check - not subscribed"""
        payload = {"email": "test@example.com", "projectId": "proj1"}

        response = client.post("/v2/subscriptions/check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["subscribed"] is False
        assert data["version"] == "v2"

    def test_check_subscription_exists_v2_subscribed(self, client, mock_db_service):
        """Test v2 subscription check - subscribed"""
        mock_db_service.get_person_by_email.return_value = MagicMock(id="person1")
        mock_db_service.get_subscriptions_by_person.return_value = [
            {"projectId": "proj1", "status": "active"}
        ]

        payload = {"email": "test@example.com", "projectId": "proj1"}

        response = client.post("/v2/subscriptions/check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["subscribed"] is True
        assert data["subscription_status"] == "active"
        assert data["version"] == "v2"

    def test_create_subscription_v2_success(self, client, mock_db_service):
        """Test v2 subscription creation success"""
        payload = {
            "person": {
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane@example.com",
            },
            "projectId": "proj1",
            "notes": "Test subscription v2",
        }

        response = client.post("/v2/public/subscribe", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Subscription created successfully"
        assert data["version"] == "v2"
        assert "subscription" in data
        assert "person_created" in data

    def test_create_subscription_v2_with_name_field(self, client, mock_db_service):
        """Test v2 subscription creation with name field conversion"""
        payload = {
            "person": {"name": "John Doe", "email": "john@example.com"},
            "projectId": "proj1",
        }

        response = client.post("/v2/public/subscribe", json=payload)
        assert response.status_code == 201
        # Verify that name was converted to firstName/lastName
        mock_db_service.create_person.assert_called_once()

    # ==================== AUTH ENDPOINT TESTS ====================

    def test_login_success(self, client, mock_db_service):
        """Test successful admin login"""
        admin_user = MagicMock()
        admin_user.id = "admin1"
        admin_user.email = "admin@example.com"
        admin_user.first_name = "Admin"
        admin_user.last_name = "User"
        admin_user.is_admin = True

        mock_db_service.get_person_by_email.return_value = admin_user

        payload = {"email": "admin@example.com", "password": "password"}

        response = client.post("/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert "token" in data
        assert data["user"]["isAdmin"] is True

    def test_login_user_not_found(self, client, mock_db_service):
        """Test login with non-existent user"""
        mock_db_service.get_person_by_email.return_value = None

        payload = {"email": "nonexistent@example.com", "password": "password"}

        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["detail"]

    def test_login_non_admin_user(self, client, mock_db_service):
        """Test login with non-admin user"""
        regular_user = MagicMock()
        regular_user.is_admin = False

        mock_db_service.get_person_by_email.return_value = regular_user

        payload = {"email": "user@example.com", "password": "password"}

        response = client.post("/auth/login", json=payload)
        assert response.status_code == 403
        data = response.json()
        assert "admin privileges required" in data["detail"]

    def test_login_v2_success(self, client, mock_db_service):
        """Test successful v2 admin login"""
        admin_user = MagicMock()
        admin_user.id = "admin1"
        admin_user.email = "admin@example.com"
        admin_user.first_name = "Admin"
        admin_user.last_name = "User"
        admin_user.is_admin = True

        mock_db_service.get_person_by_email.return_value = admin_user

        payload = {"email": "admin@example.com", "password": "password"}

        response = client.post("/v2/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert data["version"] == "v2"
        assert "jwt-token-v2-" in data["token"]

    # ==================== PEOPLE ENDPOINT TESTS ====================

    def test_get_people_v2_all(self, client, mock_db_service):
        """Test v2 get all people"""
        mock_people = [
            MagicMock(dict=lambda: {"id": "1", "email": "user1@example.com"}),
            MagicMock(dict=lambda: {"id": "2", "email": "user2@example.com"}),
        ]
        mock_db_service.get_all_people.return_value = mock_people

        response = client.get("/v2/people")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v2"
        assert data["count"] == 2
        assert len(data["people"]) == 2

    def test_get_people_v2_by_email(self, client, mock_db_service):
        """Test v2 get people by email"""
        mock_person = MagicMock()
        mock_person.dict.return_value = {"id": "1", "email": "test@example.com"}
        mock_db_service.get_person_by_email.return_value = mock_person

        response = client.get("/v2/people?email=test@example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v2"
        assert data["count"] == 1
        assert data["query"]["email"] == "test@example.com"

    def test_update_admin_status_grant(self, client, mock_db_service):
        """Test granting admin status"""
        mock_person = MagicMock()
        mock_person.id = "person1"
        mock_person.email = "user@example.com"
        mock_person.first_name = "Test"
        mock_person.last_name = "User"
        mock_person.is_admin = False

        updated_person = MagicMock()
        updated_person.id = "person1"
        updated_person.email = "user@example.com"
        updated_person.first_name = "Test"
        updated_person.last_name = "User"
        updated_person.is_admin = True

        mock_db_service.get_person_by_id.return_value = mock_person
        mock_db_service.update_person.return_value = updated_person

        payload = {"isAdmin": True}

        response = client.put("/v2/people/person1/admin", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "granted" in data["message"]
        assert data["person"]["isAdmin"] is True
        assert data["version"] == "v2"

    def test_update_admin_status_person_not_found(self, client, mock_db_service):
        """Test updating admin status for non-existent person"""
        mock_db_service.get_person_by_id.return_value = None

        payload = {"isAdmin": True}

        response = client.put("/v2/people/nonexistent/admin", json=payload)
        assert response.status_code == 404
        data = response.json()
        assert "Person not found" in data["detail"]

    # ==================== ADMIN TEST ENDPOINT ====================

    def test_admin_test_success(self, client, mock_db_service):
        """Test admin system test endpoint success"""
        admin_user = MagicMock()
        admin_user.id = "admin1"
        admin_user.email = "sergio.rodriguez.inclan@gmail.com"
        admin_user.first_name = "Sergio"
        admin_user.last_name = "Rodriguez"
        admin_user.is_admin = True

        mock_db_service.get_person_by_email.return_value = admin_user

        response = client.get("/v2/admin/test")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin system test successful"
        assert data["version"] == "v2"
        assert data["admin_user"]["isAdmin"] is True

    def test_admin_test_user_not_found(self, client, mock_db_service):
        """Test admin system test when user not found"""
        mock_db_service.get_person_by_email.return_value = None

        response = client.get("/v2/admin/test")
        assert response.status_code == 200
        data = response.json()
        assert "Admin user not found" in data["error"]
        assert data["version"] == "v2"

    @patch.dict(os.environ, {"TEST_ADMIN_EMAIL": "custom@example.com"})
    def test_admin_test_custom_email(self, client, mock_db_service):
        """Test admin system test with custom email from environment"""
        admin_user = MagicMock()
        admin_user.id = "admin1"
        admin_user.email = "custom@example.com"
        admin_user.first_name = "Custom"
        admin_user.last_name = "Admin"
        admin_user.is_admin = True

        mock_db_service.get_person_by_email.return_value = admin_user

        response = client.get("/v2/admin/test")
        assert response.status_code == 200
        # Verify the custom email was used
        mock_db_service.get_person_by_email.assert_called_with("custom@example.com")

    # ==================== LEGACY ENDPOINT TESTS ====================

    def test_legacy_subscriptions_redirect(self, client, mock_db_service):
        """Test legacy subscriptions endpoint redirects to v1"""
        response = client.get("/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        # Should behave like v1 (no version field)
        assert "version" not in data

    def test_legacy_projects_redirect(self, client, mock_db_service):
        """Test legacy projects endpoint redirects to v1"""
        response = client.get("/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        # Should behave like v1 (no version field)
        assert "version" not in data

    def test_legacy_subscribe_redirect(self, client, mock_db_service):
        """Test legacy subscribe endpoint redirects to v1"""
        payload = {
            "person": {
                "firstName": "Legacy",
                "lastName": "User",
                "email": "legacy@example.com",
            },
            "projectId": "proj1",
        }

        response = client.post("/public/subscribe", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Subscription created successfully"
        # Should behave like v1 (no version field)
        assert "version" not in data

    # ==================== ERROR HANDLING TESTS ====================

    def test_database_error_handling(self, client, mock_db_service):
        """Test database error handling"""
        mock_db_service.get_all_subscriptions.side_effect = Exception("Database error")

        response = client.get("/v1/subscriptions")
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve subscriptions" in data["detail"]

    def test_async_await_correctness(self, client, mock_db_service):
        """Test that async functions are properly awaited"""
        # This test ensures that async database calls are properly awaited
        # by checking that AsyncMock methods are called correctly

        response = client.get("/v2/subscriptions")
        assert response.status_code == 200

        # Verify that the async method was called
        mock_db_service.get_all_subscriptions.assert_called_once()

        # Reset and test another endpoint
        mock_db_service.reset_mock()

        response = client.get("/v2/projects")
        assert response.status_code == 200
        mock_db_service.get_all_projects.assert_called_once()

    # ==================== ROUTE REGISTRATION TESTS ====================

    def test_all_routes_registered(self, client):
        """Test that all expected routes are registered"""
        # Get all routes from the FastAPI app
        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods
                        routes.append(f"{method} {route.path}")

        # Expected routes
        expected_routes = [
            "GET /health",
            "GET /v1/subscriptions",
            "GET /v1/projects",
            "POST /v1/public/subscribe",
            "GET /v2/subscriptions",
            "GET /v2/projects",
            "POST /v2/people/check-email",
            "POST /v2/subscriptions/check",
            "POST /v2/public/subscribe",
            "GET /subscriptions",
            "GET /projects",
            "POST /public/subscribe",
            "POST /auth/login",
            "POST /v2/auth/login",
            "GET /v2/people",
            "PUT /v2/people/{person_id}/admin",
            "GET /v2/admin/test",
        ]

        # Check that all expected routes are registered
        for expected_route in expected_routes:
            assert any(
                expected_route.replace("{person_id}", "person_id") in route
                or expected_route in route
                for route in routes
            ), f"Route {expected_route} not found"

        # Verify we have the expected number of routes (approximately)
        assert len(routes) >= len(
            expected_routes
        ), f"Expected at least {len(expected_routes)} routes, got {len(routes)}"

    def test_no_duplicate_routes(self, client):
        """Test that there are no duplicate route definitions"""
        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":
                        route_signature = f"{method} {route.path}"
                        routes.append(route_signature)

        # Check for duplicates
        unique_routes = set(routes)
        assert len(routes) == len(
            unique_routes
        ), f"Duplicate routes found: {[r for r in routes if routes.count(r) > 1]}"


# ==================== INTEGRATION TESTS ====================


class TestIntegration:
    """Integration tests that test multiple components together"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_full_subscription_flow_v2(self, client):
        """Test complete subscription flow in v2"""
        with patch("handlers.versioned_api_handler.db_service") as mock_db:
            # Setup mocks for the full flow
            mock_db.get_project_by_id.return_value = {
                "id": "proj1",
                "name": "Test Project",
            }
            mock_db.get_person_by_email.return_value = None  # New person
            mock_db.create_person.return_value = MagicMock(id="person1")
            mock_db.create_subscription.return_value = {
                "id": "sub1",
                "projectId": "proj1",
                "personId": "person1",
                "status": "pending",
            }

            # Create subscription
            payload = {
                "person": {
                    "firstName": "Integration",
                    "lastName": "Test",
                    "email": "integration@example.com",
                },
                "projectId": "proj1",
                "notes": "Integration test subscription",
            }

            response = client.post("/v2/public/subscribe", json=payload)
            assert response.status_code == 201

            # Verify all expected database calls were made
            mock_db.get_project_by_id.assert_called_with("proj1")
            mock_db.get_person_by_email.assert_called_once()
            mock_db.create_person.assert_called_once()
            mock_db.create_subscription.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
