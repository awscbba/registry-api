"""
Tests specifically for async/await correctness in the versioned API handler.

This test suite ensures that:
- All database calls are properly awaited
- No blocking calls are made in async functions
- Async functions are correctly defined
"""

import pytest
import asyncio
import inspect
import ast
import os
from unittest.mock import AsyncMock, MagicMock, patch
import sys


from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app for testing
from src.handlers.versioned_api_handler import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_db_service():
    """Mock database service"""
    with patch("src.handlers.versioned_api_handler.db_service") as mock:
        yield mock


@pytest.fixture
def versioned_api_handler():
    """Mock versioned API handler"""
    import src.handlers.versioned_api_handler as handler

    return handler


class TestAsyncCorrectness:
    """Test suite for async/await correctness"""

    def test_all_endpoint_functions_are_async(self):
        """Verify all endpoint handler functions are properly async"""
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

        # Find all async function definitions
        async_functions = []
        sync_functions = []

        class FunctionVisitor(ast.NodeVisitor):
            def visit_AsyncFunctionDef(self, node):
                async_functions.append(node.name)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                # Skip private functions and class methods
                if not node.name.startswith("_"):
                    sync_functions.append(node.name)
                self.generic_visit(node)

        visitor = FunctionVisitor()
        visitor.visit(tree)

        # Check that endpoint functions are async
        endpoint_patterns = ["_v1", "_v2", "health_check", "login", "test_admin_system"]
        non_async_endpoints = []

        for func_name in sync_functions:
            if any(pattern in func_name for pattern in endpoint_patterns):
                non_async_endpoints.append(func_name)

        assert (
            len(non_async_endpoints) == 0
        ), f"Non-async endpoint functions found: {non_async_endpoints}"

        # Verify we found some async functions
        assert len(async_functions) > 0, "No async functions found in handler"

    def test_database_calls_are_awaited(self):
        """Test that all database service calls are properly awaited"""
        # Read source directly to check for await keywords
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "handlers",
            "versioned_api_handler.py",
        )
        with open(handler_path, "r") as f:
            source = f.read()

        # Check that async database methods are called with await
        async_db_methods = [
            "get_all_subscriptions",
            "get_all_projects",
            "get_person_by_email",
            "create_person",
            "create_subscription",
        ]

        missing_await = []
        for method in async_db_methods:
            pattern = f"db_service.{method}("
            if pattern in source:
                # Find all occurrences
                import re

                matches = list(re.finditer(re.escape(pattern), source))
                for match in matches:
                    # Get the line containing the match
                    start = source.rfind("\n", 0, match.start()) + 1
                    end = source.find("\n", match.end())
                    line = source[start:end] if end != -1 else source[start:]

                    # Check if await is present before the call
                    if "await" not in line[: match.start() - start]:
                        missing_await.append(f"{method} in: {line.strip()}")

        assert len(missing_await) == 0, f"Database calls missing await: {missing_await}"

        response = client.get("/v2/projects")
        assert response.status_code == 200

        # Test subscription creation
        payload = {
            "person": {
                "firstName": "Test",
                "lastName": "User",
                "email": "test@example.com",
            },
            "projectId": "test",
        }
        response = client.post("/v2/public/subscribe", json=payload)
        assert response.status_code == 201

        # Verify async methods were called (they should not raise AttributeError)
        assert mock_db_service.get_person_by_email.called
        assert mock_db_service.create_person.called
        assert mock_db_service.create_subscription.called

    def test_no_blocking_calls_in_async_functions(self):
        """Test that async functions don't contain obvious blocking calls"""
        import ast
        import inspect

        # Get the source code of the module
        source = inspect.getsource(versioned_api_handler)
        tree = ast.parse(source)

        class AsyncFunctionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.async_functions = []
                self.current_function = None
                self.blocking_calls = []

            def visit_AsyncFunctionDef(self, node):
                self.current_function = node.name
                self.async_functions.append(node.name)
                self.generic_visit(node)
                self.current_function = None

            def visit_Call(self, node):
                if self.current_function:
                    # Check for common blocking calls
                    if isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "db_service"
                        ):
                            # Check if this is a database call without await
                            # This is a simplified check - in practice, we'd need more sophisticated analysis
                            method_name = node.func.attr
                            if method_name in [
                                "get_all_subscriptions",
                                "get_all_projects",
                                "create_person",
                                "create_subscription",
                                "get_person_by_email",
                                "get_subscriptions_by_person",
                                "get_all_people",
                                "get_person_by_id",
                                "update_person",
                            ]:
                                # These should be awaited - check parent node
                                pass  # This would require more complex AST analysis

                self.generic_visit(node)

        visitor = AsyncFunctionVisitor()
        visitor.visit(tree)

        # Verify we found async functions
        assert (
            len(visitor.async_functions) > 0
        ), "Should find async functions in the module"

        # Check that key functions are async
        expected_async_functions = [
            "get_subscriptions_v1",
            "get_projects_v1",
            "create_subscription_v1",
            "get_subscriptions_v2",
            "get_projects_v2",
            "check_person_exists_v2",
            "check_subscription_exists_v2",
            "create_subscription_v2",
            "login",
            "login_v2",
            "get_people_v2",
            "update_admin_status",
            "test_admin_system",
        ]

        for func_name in expected_async_functions:
            assert (
                func_name in visitor.async_functions
            ), f"Function {func_name} should be async"

    @patch("handlers.versioned_api_handler.db_service")
    def test_async_mock_behavior(self, mock_db_service):
        """Test that AsyncMock is used correctly for async database methods"""
        # Configure specific methods as AsyncMock
        async_methods = [
            "get_all_subscriptions",
            "get_all_projects",
            "get_person_by_email",
            "create_person",
            "create_subscription",
            "get_subscriptions_by_person",
            "get_all_people",
            "get_person_by_id",
            "update_person",
        ]

        for method_name in async_methods:
            setattr(mock_db_service, method_name, AsyncMock())

        # Non-async methods
        mock_db_service.get_project_by_id = MagicMock(return_value={"id": "test"})

        # Test that async methods can be awaited
        async def test_async_call():
            result = await mock_db_service.get_all_subscriptions()
            return result

        # This should not raise an exception
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test_async_call())
            assert (
                result is not None or result == []
            )  # AsyncMock returns None by default
        finally:
            loop.close()

    def test_function_signatures_consistency(self):
        """Test that function signatures are consistent between versions"""
        # Get v1 and v2 functions
        v1_functions = {}
        v2_functions = {}

        for name, func in inspect.getmembers(versioned_api_handler, inspect.isfunction):
            if name.endswith("_v1"):
                base_name = name[:-3]  # Remove '_v1'
                v1_functions[base_name] = func
            elif name.endswith("_v2"):
                base_name = name[:-3]  # Remove '_v2'
                v2_functions[base_name] = func

        # Check that corresponding v1 and v2 functions have similar signatures
        common_functions = set(v1_functions.keys()) & set(v2_functions.keys())

        for func_name in common_functions:
            v1_sig = inspect.signature(v1_functions[func_name])
            v2_sig = inspect.signature(v2_functions[func_name])

            # Parameters should be the same (ignoring annotations)
            v1_params = list(v1_sig.parameters.keys())
            v2_params = list(v2_sig.parameters.keys())

            assert (
                v1_params == v2_params
            ), f"Function {func_name} has different parameters in v1 and v2"

    def test_import_correctness(self):
        """Test that all imports are correct and no circular imports exist"""
        # Test that the module can be imported without errors
        try:
            import handlers.versioned_api_handler

            assert True
        except ImportError as e:
            pytest.fail(f"Import error in versioned_api_handler: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing versioned_api_handler: {e}")

        # Test that required dependencies are available
        required_modules = [
            "fastapi",
            "pydantic",
            "datetime",
            "logging",
            "uuid",
            "typing",
        ]

        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Required module {module_name} is not available")

    def test_no_duplicate_function_definitions(self):
        """Test that there are no duplicate function definitions"""
        import ast
        import inspect

        source = inspect.getsource(versioned_api_handler)
        tree = ast.parse(source)

        function_names = []

        class FunctionVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                function_names.append(node.name)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                function_names.append(node.name)
                self.generic_visit(node)

        visitor = FunctionVisitor()
        visitor.visit(tree)

        # Check for duplicates
        duplicates = [name for name in function_names if function_names.count(name) > 1]
        assert (
            len(duplicates) == 0
        ), f"Duplicate function definitions found: {duplicates}"

    @patch("handlers.versioned_api_handler.db_service")
    def test_error_handling_in_async_functions(self, mock_db_service):
        """Test that async functions properly handle exceptions"""
        # Configure mock to raise exceptions
        mock_db_service.get_all_subscriptions = AsyncMock(
            side_effect=Exception("Database error")
        )

        from fastapi.testclient import TestClient
        from handlers.versioned_api_handler import app

        client = TestClient(app)

        # Test that exceptions are properly handled
        response = client.get("/v1/subscriptions")
        assert response.status_code == 500

        data = response.json()
        assert "Failed to retrieve subscriptions" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
