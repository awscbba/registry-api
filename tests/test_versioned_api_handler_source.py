"""
Source code validation tests for versioned_api_handler.py

This test suite validates the source code structure without importing the module,
avoiding relative import issues in CI/CD environments.
"""

import pytest
import ast
import os
import re
from pathlib import Path


class TestVersionedAPIHandlerSource:
    """Test suite for versioned API handler source validation"""

    @pytest.fixture
    def handler_source_path(self):
        """Get the path to the versioned API handler source file"""
        test_dir = Path(__file__).parent
        handler_path = test_dir.parent / "src" / "handlers" / "versioned_api_handler.py"
        return handler_path

    @pytest.fixture
    def handler_source(self, handler_source_path):
        """Read the source code of the versioned API handler"""
        with open(handler_source_path, "r") as f:
            return f.read()

    def test_source_file_exists(self, handler_source_path):
        """Test that the versioned API handler source file exists"""
        assert (
            handler_source_path.exists()
        ), f"Source file not found: {handler_source_path}"

    def test_source_file_is_valid_python(self, handler_source):
        """Test that the source file contains valid Python syntax"""
        try:
            ast.parse(handler_source)
        except SyntaxError as e:
            pytest.fail(f"Source file contains syntax errors: {e}")

    def test_has_required_imports(self, handler_source):
        """Test that the handler has required imports"""
        required_imports = [
            "from fastapi import FastAPI",
            "from ..services.dynamodb_service import DynamoDBService",
            "from ..utils.error_handler import",
            "from ..utils.logging_config import",
            "from ..utils.response_models import",
        ]

        for import_stmt in required_imports:
            assert (
                import_stmt in handler_source
            ), f"Missing required import: {import_stmt}"

    def test_has_fastapi_app(self, handler_source):
        """Test that the handler creates a FastAPI app"""
        assert "app = FastAPI(" in handler_source, "FastAPI app not created"
        assert "title=" in handler_source, "FastAPI app missing title"

    def test_has_version_routers(self, handler_source):
        """Test that the handler has v1 and v2 routers"""
        assert "v1_router = APIRouter(" in handler_source, "v1 router not found"
        assert "v2_router = APIRouter(" in handler_source, "v2 router not found"
        assert (
            "app.include_router(v1_router" in handler_source
        ), "v1 router not included"
        assert (
            "app.include_router(v2_router" in handler_source
        ), "v2 router not included"

    def test_has_health_endpoint(self, handler_source):
        """Test that the handler has a health check endpoint"""
        assert '@app.get("/health")' in handler_source, "Health endpoint not found"
        assert (
            "async def health_check" in handler_source
        ), "Health check function not found"

    def test_has_v1_endpoints(self, handler_source):
        """Test that the handler has v1 endpoints"""
        v1_endpoints = [
            '@v1_router.get("/subscriptions")',
            '@v1_router.get("/projects")',
            '@v1_router.post("/public/subscribe")',
        ]

        for endpoint in v1_endpoints:
            assert endpoint in handler_source, f"Missing v1 endpoint: {endpoint}"

    def test_has_v2_endpoints(self, handler_source):
        """Test that the handler has v2 endpoints"""
        v2_endpoints = [
            '@v2_router.get("/subscriptions")',
            '@v2_router.get("/projects")',
            '@v2_router.post("/public/subscribe"',  # Allow for additional parameters
            '@v2_router.post("/people/check-email")',
            '@v2_router.post("/subscriptions/check")',
        ]

        for endpoint in v2_endpoints:
            assert endpoint in handler_source, f"Missing v2 endpoint: {endpoint}"

    def test_has_admin_endpoints(self, handler_source):
        """Test that the handler has admin endpoints"""
        admin_endpoints = [
            '@v2_router.get("/admin/test")',
            '@v2_router.get("/people")',
            '@v2_router.put("/people/{person_id}/admin")',
        ]

        for endpoint in admin_endpoints:
            assert endpoint in handler_source, f"Missing admin endpoint: {endpoint}"

    def test_async_functions_properly_defined(self, handler_source):
        """Test that all endpoint functions are properly async"""
        tree = ast.parse(handler_source)

        async_functions = []
        sync_functions = []

        class FunctionVisitor(ast.NodeVisitor):
            def visit_AsyncFunctionDef(self, node):
                async_functions.append(node.name)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                if not node.name.startswith("_"):
                    sync_functions.append(node.name)
                self.generic_visit(node)

        visitor = FunctionVisitor()
        visitor.visit(tree)

        # All endpoint functions should be async
        endpoint_patterns = ["_v1", "_v2", "health_check", "login", "test_admin_system"]
        non_async_endpoints = []

        for func_name in sync_functions:
            if any(pattern in func_name for pattern in endpoint_patterns):
                non_async_endpoints.append(func_name)

        assert (
            len(non_async_endpoints) == 0
        ), f"Non-async endpoint functions: {non_async_endpoints}"
        assert (
            len(async_functions) > 5
        ), f"Expected more async functions, found: {len(async_functions)}"

    def test_database_calls_have_proper_await(self, handler_source):
        """Test that database calls use proper await keywords"""
        # Methods that should be awaited
        async_db_methods = [
            "check_email_uniqueness",
            "clear_account_lockout",
            "create_person",
            "delete_person",
            "get_account_lockout",
            "get_all_projects",
            "get_all_subscriptions",
            "get_person",
            "get_person_by_email",
            "list_people",
            "log_security_event",
            "save_account_lockout",
            "search_people",
            "update_last_login",
            "update_person",
            "update_person_password_fields",
        ]

        # Methods that should NOT be awaited (sync methods)
        sync_db_methods = ["get_project_by_id"]

        missing_await = []
        incorrect_await = []

        for method in async_db_methods:
            pattern = f"db_service.{method}("
            if pattern in handler_source:
                # Find all occurrences
                matches = list(re.finditer(re.escape(pattern), handler_source))
                for match in matches:
                    # Get the line containing the match
                    start = handler_source.rfind("\n", 0, match.start()) + 1
                    end = handler_source.find("\n", match.end())
                    line = (
                        handler_source[start:end]
                        if end != -1
                        else handler_source[start:]
                    )

                    # Check if await is present before the call
                    if "await" not in line[: match.start() - start]:
                        missing_await.append(f"{method} in: {line.strip()}")

        for method in sync_db_methods:
            pattern = f"await db_service.{method}("
            if pattern in handler_source:
                incorrect_await.append(f"Sync method {method} should not use await")

        assert len(missing_await) == 0, f"Database calls missing await: {missing_await}"
        assert (
            len(incorrect_await) == 0
        ), f"Sync methods incorrectly using await: {incorrect_await}"

    def test_uses_standardized_components(self, handler_source):
        """Test that the handler uses standardized components"""
        standardized_components = [
            "StandardErrorHandler",
            "handle_database_error",
            "get_handler_logger",
            "ResponseFactory",
            "create_v1_response",
            "create_v2_response",
        ]

        for component in standardized_components:
            assert (
                component in handler_source
            ), f"Missing standardized component: {component}"

    def test_has_proper_error_handling(self, handler_source):
        """Test that the handler has proper error handling patterns"""
        # Should have try/except blocks
        assert "try:" in handler_source, "No try blocks found"
        assert "except Exception as e:" in handler_source, "No exception handling found"

        # Should use standardized error handling
        assert (
            "handle_database_error" in handler_source
        ), "Not using standardized database error handling"

        # Should have logging
        assert "logger.error" in handler_source, "No error logging found"

    def test_version_information_in_responses(self, handler_source):
        """Test that v2 endpoints include version information"""
        # V2 endpoints should include version in responses
        v2_version_patterns = ['"version": "v2"', "'version': 'v2'"]

        found_version_info = any(
            pattern in handler_source for pattern in v2_version_patterns
        )
        assert (
            found_version_info
        ), "V2 endpoints should include version information in responses"

    def test_cors_middleware_configured(self, handler_source):
        """Test that CORS middleware is properly configured"""
        assert "CORSMiddleware" in handler_source, "CORS middleware not imported"
        assert "add_middleware" in handler_source, "CORS middleware not added"
        assert "allow_origins" in handler_source, "CORS origins not configured"
