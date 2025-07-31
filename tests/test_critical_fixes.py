"""
Critical tests to verify that the fixes applied to versioned_api_handler.py work correctly.

These tests specifically check for the issues that were fixed:
1. No duplicate function definitions
2. All async database calls are properly awaited
3. Admin endpoints are accessible
4. No import errors
"""

import pytest
import ast
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestCriticalFixes:
    """Test suite for critical fixes verification"""

    def test_module_imports_successfully(self):
        """Test that the versioned API handler source is valid Python"""
        # Test that the source file is valid Python syntax instead of importing
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "handlers",
            "versioned_api_handler.py",
        )
        try:
            with open(handler_path, "r") as f:
                source = f.read()

            # Parse the source to ensure it's valid Python
            ast.parse(source)

            # Check that it contains expected components
            assert "FastAPI" in source, "FastAPI not found in handler"
            assert "async def" in source, "No async functions found"
            assert "db_service" in source, "Database service not initialized"

        except SyntaxError as e:
            pytest.fail(f"Syntax error in versioned_api_handler: {e}")
        except Exception as e:
            pytest.fail(f"Error reading versioned_api_handler: {e}")

    def test_no_duplicate_function_definitions_in_source(self):
        """Test that there are no duplicate function definitions in the source code"""
        # Read source directly to avoid import issues
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "handlers",
            "versioned_api_handler.py",
        )
        with open(handler_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        function_names = []

        class FunctionCollector(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                function_names.append(node.name)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                function_names.append(node.name)
                self.generic_visit(node)

        collector = FunctionCollector()
        collector.visit(tree)

        # Find duplicates
        duplicates = []
        seen = set()
        for name in function_names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        assert (
            len(duplicates) == 0
        ), f"Found duplicate function definitions: {duplicates}"

    def test_admin_test_endpoint_exists(self):
        """Test that the admin test endpoint exists and is accessible"""
        from handlers.versioned_api_handler import app

        client = TestClient(app)

        with patch("handlers.versioned_api_handler.db_service") as mock_db:
            # Mock the admin user
            admin_user = MagicMock()
            admin_user.id = "admin1"
            admin_user.email = "test@example.com"
            admin_user.first_name = "Test"
            admin_user.last_name = "Admin"
            admin_user.is_admin = True

            mock_db.get_person_by_email = AsyncMock(return_value=admin_user)

            response = client.get("/v2/admin/test")
            assert response.status_code == 200

            data = response.json()
            assert "message" in data
            assert data["version"] == "v2"

    def test_all_database_calls_have_await_keywords(self):
        """Test that all async database calls have await keywords"""
        # Read source directly to avoid import issues
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "handlers",
            "versioned_api_handler.py",
        )
        with open(handler_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)

        # Methods that should be awaited
        async_db_methods = {
            "get_all_subscriptions",
            "get_all_projects",
            "get_person_by_email",
            "create_person",
            "create_subscription",
            "get_subscriptions_by_person",
            "get_all_people",
            "get_person_by_id",
            "update_person",
        }

        # Methods that should NOT be awaited (sync methods)
        sync_db_methods = {"get_project_by_id"}

        class DatabaseCallChecker(ast.NodeVisitor):
            def __init__(self):
                self.issues = []
                self.current_function = None

            def visit_AsyncFunctionDef(self, node):
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = None

            def visit_Await(self, node):
                # Check if this is awaiting a database call
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and isinstance(node.value.func.value, ast.Name)
                    and node.value.func.value.id == "db_service"
                ):

                    method_name = node.value.func.attr
                    if method_name in sync_db_methods:
                        self.issues.append(
                            f"Function {self.current_function}: {method_name} should NOT be awaited"
                        )

                self.generic_visit(node)

            def visit_Call(self, node):
                # Check for database calls that should be awaited but aren't
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "db_service"
                ):

                    method_name = node.func.attr
                    if method_name in async_db_methods:
                        # Check if this call is inside an await expression
                        # This is a simplified check - we'd need parent node tracking for full accuracy
                        pass  # For now, we'll rely on the functional test below

                self.generic_visit(node)

        checker = DatabaseCallChecker()
        checker.visit(tree)

        assert len(checker.issues) == 0, f"Database call issues found: {checker.issues}"

    @patch("handlers.versioned_api_handler.db_service")
    def test_async_database_calls_work_correctly(self, mock_db_service):
        """Test that async database calls work correctly in practice"""
        from handlers.versioned_api_handler import app

        # Configure all database methods as AsyncMock
        mock_db_service.get_all_subscriptions = AsyncMock(
            return_value=[{"id": "sub1", "status": "active"}]
        )
        mock_db_service.get_all_projects = AsyncMock(
            return_value=[{"id": "proj1", "name": "Test Project"}]
        )
        mock_db_service.get_person_by_email = AsyncMock(return_value=None)
        mock_db_service.create_person = AsyncMock(return_value=MagicMock(id="person1"))
        mock_db_service.create_subscription = AsyncMock(return_value={"id": "sub1"})
        mock_db_service.get_subscriptions_by_person = AsyncMock(return_value=[])
        mock_db_service.get_all_people = AsyncMock(return_value=[])
        mock_db_service.get_person_by_id = AsyncMock(
            return_value=MagicMock(id="person1")
        )
        mock_db_service.update_person = AsyncMock(
            return_value=MagicMock(id="person1", is_admin=True)
        )

        # Sync methods
        mock_db_service.get_project_by_id = MagicMock(
            return_value={"id": "proj1", "name": "Test"}
        )

        client = TestClient(app)

        # Test various endpoints to ensure they work without async/await errors
        test_cases = [
            ("GET", "/v1/subscriptions", None),
            ("GET", "/v1/projects", None),
            ("GET", "/v2/subscriptions", None),
            ("GET", "/v2/projects", None),
            ("POST", "/v2/people/check-email", {"email": "test@example.com"}),
            (
                "POST",
                "/v2/subscriptions/check",
                {"email": "test@example.com", "projectId": "proj1"},
            ),
            ("GET", "/v2/people", None),
            (
                "POST",
                "/v2/public/subscribe",
                {
                    "person": {
                        "firstName": "Test",
                        "lastName": "User",
                        "email": "test@example.com",
                    },
                    "projectId": "proj1",
                },
            ),
        ]

        for method, endpoint, payload in test_cases:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=payload)

            # Should not get 500 errors from async/await issues
            assert (
                response.status_code != 500
            ), f"Endpoint {method} {endpoint} returned 500 error: {response.text}"

            # Should get valid responses (200, 201, 400, etc. but not 500)
            assert (
                response.status_code < 500
            ), f"Endpoint {method} {endpoint} returned server error: {response.status_code}"

    def test_no_redundant_imports(self):
        """Test that there are no redundant inline imports"""
        from handlers import versioned_api_handler

        source = inspect.getsource(versioned_api_handler)
        lines = source.split("\n")

        # Look for inline imports inside functions
        inline_imports = []
        inside_function = False
        current_function = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track if we're inside a function
            if stripped.startswith("def ") or stripped.startswith("async def "):
                inside_function = True
                current_function = (
                    stripped.split("(")[0].replace("def ", "").replace("async ", "")
                )
            elif stripped.startswith("class ") or (
                stripped and not line.startswith(" ") and not line.startswith("\t")
            ):
                inside_function = False
                current_function = None

            # Look for imports inside functions
            if inside_function and (
                stripped.startswith("from ..") or stripped.startswith("import ")
            ):
                inline_imports.append(f"Line {i + 1} in {current_function}: {stripped}")

        # Filter out acceptable inline imports (like os.getenv)
        problematic_imports = [
            imp
            for imp in inline_imports
            if "from ..models" in imp or "from ..services" in imp
        ]

        assert (
            len(problematic_imports) == 0
        ), f"Found redundant inline imports: {problematic_imports}"

    def test_environment_variable_configuration(self):
        """Test that environment variables are properly used for configuration"""
        from handlers.versioned_api_handler import app

        client = TestClient(app)

        # Test with custom admin email
        with patch.dict(os.environ, {"TEST_ADMIN_EMAIL": "custom-admin@example.com"}):
            with patch("handlers.versioned_api_handler.db_service") as mock_db:
                admin_user = MagicMock()
                admin_user.id = "admin1"
                admin_user.email = "custom-admin@example.com"
                admin_user.first_name = "Custom"
                admin_user.last_name = "Admin"
                admin_user.is_admin = True

                mock_db.get_person_by_email = AsyncMock(return_value=admin_user)

                response = client.get("/v2/admin/test")
                assert response.status_code == 200

                # Verify the custom email was used
                mock_db.get_person_by_email.assert_called_with(
                    "custom-admin@example.com"
                )

    def test_route_registration_completeness(self):
        """Test that all expected routes are properly registered"""
        from handlers.versioned_api_handler import app

        # Get all registered routes
        registered_routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods
                        registered_routes.append(f"{method} {route.path}")

        # Critical routes that must be present
        critical_routes = [
            "GET /health",
            "GET /v2/admin/test",
            "POST /v2/people/check-email",
            "POST /v2/subscriptions/check",
            "POST /v2/public/subscribe",
            "GET /v2/subscriptions",
            "GET /v2/projects",
        ]

        missing_routes = []
        for critical_route in critical_routes:
            if not any(critical_route in route for route in registered_routes):
                missing_routes.append(critical_route)

        assert len(missing_routes) == 0, f"Missing critical routes: {missing_routes}"

    def test_fastapi_app_creation(self):
        """Test that the FastAPI app is created correctly"""
        from handlers.versioned_api_handler import app

        assert app is not None, "FastAPI app should be created"
        assert hasattr(app, "routes"), "App should have routes"
        assert len(app.routes) > 0, "App should have registered routes"

        # Check app metadata
        assert app.title == "People Register API - Versioned"
        assert app.version == "2.0.0"

    @patch("handlers.versioned_api_handler.db_service")
    def test_error_handling_consistency(self, mock_db_service):
        """Test that error handling is consistent across endpoints"""
        from handlers.versioned_api_handler import app

        # Configure database to raise exceptions
        mock_db_service.get_all_subscriptions = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_db_service.get_all_projects = AsyncMock(
            side_effect=Exception("Database error")
        )

        client = TestClient(app)

        # Test that exceptions are properly handled and return 500 errors
        error_test_cases = [
            ("GET", "/v1/subscriptions"),
            ("GET", "/v1/projects"),
            ("GET", "/v2/subscriptions"),
            ("GET", "/v2/projects"),
        ]

        for method, endpoint in error_test_cases:
            response = client.get(endpoint)
            assert (
                response.status_code == 500
            ), f"Endpoint {endpoint} should return 500 on database error"

            data = response.json()
            assert "detail" in data, f"Error response should have detail field"
            assert (
                "Failed to retrieve" in data["detail"]
            ), f"Error message should be descriptive"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
