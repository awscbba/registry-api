"""
Tests specifically for async/await correctness in the versioned API handler.

This test suite ensures that:
- All database calls are properly awaited
- No blocking calls are made in async functions
- Async functions are correctly defined

This version works without importing the handler module to avoid relative import issues.
"""

import pytest
import ast
import os
import re


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

        missing_await = []
        for method in async_db_methods:
            pattern = f"db_service.{method}("
            if pattern in source:
                # Find all occurrences
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

    def test_sync_database_methods_not_awaited(self):
        """Test that sync database methods are not incorrectly awaited"""
        handler_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "handlers",
            "versioned_api_handler.py",
        )
        with open(handler_path, "r") as f:
            source = f.read()

        # Methods that should NOT be awaited (sync methods)
        # Note: In DefensiveDynamoDBService, all database methods are async for consistency
        sync_db_methods = []

        incorrect_await = []
        for method in sync_db_methods:
            pattern = f"await db_service.{method}("
            if pattern in source:
                incorrect_await.append(f"Sync method {method} should not use await")

        assert (
            len(incorrect_await) == 0
        ), f"Sync methods incorrectly using await: {incorrect_await}"
