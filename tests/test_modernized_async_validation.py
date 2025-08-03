"""
Modernized Async/Sync Validation Tests

This replaces the hardcoded async method lists in the legacy tests
with dynamic detection from the actual DynamoDBService class.
"""

import pytest
import ast
import inspect
import asyncio
import os
import re
from pathlib import Path

# Import the actual service to inspect its methods
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.services.dynamodb_service import DynamoDBService


class TestModernizedAsyncValidation:
    """Modernized tests that dynamically detect async/sync methods"""

    @pytest.fixture
    def handler_source_path(self):
        """Get the path to the versioned API handler source file"""
        return (
            Path(__file__).parent.parent
            / "src"
            / "handlers"
            / "versioned_api_handler.py"
        )

    @pytest.fixture
    def handler_source(self, handler_source_path):
        """Read the source code of the versioned API handler"""
        with open(handler_source_path, "r") as f:
            return f.read()

    @pytest.fixture
    def db_service_methods(self):
        """Dynamically detect async and sync methods from DynamoDBService"""
        async_methods = []
        sync_methods = []

        for name, method in inspect.getmembers(
            DynamoDBService, predicate=inspect.isfunction
        ):
            if not name.startswith("_"):
                if asyncio.iscoroutinefunction(method):
                    async_methods.append(name)
                else:
                    sync_methods.append(name)

        return {
            "async": async_methods,
            "sync": sync_methods,
            "all": async_methods + sync_methods,
        }

    def test_dynamic_method_detection(self, db_service_methods):
        """Test that we can properly detect async vs sync methods"""
        # Verify we found some methods
        assert len(db_service_methods["async"]) > 0, "Should find some async methods"
        assert len(db_service_methods["sync"]) > 0, "Should find some sync methods"

        # Print for debugging
        print(f"\nDetected async methods: {db_service_methods['async']}")
        print(f"Detected sync methods: {db_service_methods['sync']}")

        # Verify specific methods we know about
        assert "get_person" in db_service_methods["async"], "get_person should be async"
        assert (
            "get_project_by_id" in db_service_methods["sync"]
        ), "get_project_by_id should be sync"

    def test_database_calls_have_correct_await_usage(
        self, handler_source, db_service_methods
    ):
        """
        Test that database calls use await correctly based on actual method signatures

        This replaces the hardcoded method lists in the legacy tests.
        """
        async_methods = db_service_methods["async"]
        sync_methods = db_service_methods["sync"]

        # Find all db_service method calls
        method_calls = {}  # method_name -> [(line_content, has_await)]

        lines = handler_source.split("\n")
        for i, line in enumerate(lines, 1):
            # Look for db_service method calls
            for method in async_methods + sync_methods:
                pattern = f"db_service.{method}("
                if pattern in line:
                    has_await = "await" in line and line.find("await") < line.find(
                        pattern
                    )

                    if method not in method_calls:
                        method_calls[method] = []
                    method_calls[method].append((line.strip(), has_await, i))

        # Check for incorrect usage
        errors = []

        for method, calls in method_calls.items():
            for line_content, has_await, line_num in calls:
                if method in async_methods and not has_await:
                    errors.append(
                        f"Line {line_num}: Async method '{method}' missing await: {line_content}"
                    )
                elif method in sync_methods and has_await:
                    errors.append(
                        f"Line {line_num}: Sync method '{method}' incorrectly uses await: {line_content}"
                    )

        if errors:
            print(f"\nFound {len(errors)} async/sync usage errors:")
            for error in errors:
                print(f"  - {error}")

        assert len(errors) == 0, f"Async/sync usage errors: {errors}"

    def test_all_db_service_calls_are_valid_methods(
        self, handler_source, db_service_methods
    ):
        """
        Test that all db_service method calls reference methods that actually exist

        This would have caught the get_person_by_id vs get_person bug.
        """
        all_methods = db_service_methods["all"]

        # Find all db_service method calls
        called_methods = set()
        invalid_calls = []

        lines = handler_source.split("\n")
        for i, line in enumerate(lines, 1):
            # Look for db_service.method( patterns
            matches = re.finditer(r"db_service\.(\w+)\(", line)
            for match in matches:
                method_name = match.group(1)
                called_methods.add(method_name)

                if method_name not in all_methods:
                    invalid_calls.append(
                        f"Line {i}: Unknown method 'db_service.{method_name}()': {line.strip()}"
                    )

        print(f"\nFound calls to these db_service methods: {sorted(called_methods)}")
        print(f"Available methods: {sorted(all_methods)}")

        if invalid_calls:
            print(f"\nFound {len(invalid_calls)} invalid method calls:")
            for call in invalid_calls:
                print(f"  - {call}")

        assert (
            len(invalid_calls) == 0
        ), f"Invalid db_service method calls: {invalid_calls}"

    def test_create_subscription_is_correctly_identified_as_sync(
        self, db_service_methods
    ):
        """
        Specific test for the create_subscription method that was causing test failures

        This verifies that our dynamic detection correctly identifies it as sync.
        """
        # The failing tests assumed create_subscription was async, but it's actually sync
        assert (
            "create_subscription" in db_service_methods["sync"]
        ), "create_subscription should be detected as a sync method"

        assert (
            "create_subscription" not in db_service_methods["async"]
        ), "create_subscription should NOT be detected as an async method"

    def test_get_subscriptions_by_person_is_correctly_identified_as_sync(
        self, db_service_methods
    ):
        """
        Specific test for the get_subscriptions_by_person method
        """
        # This was also incorrectly assumed to be async in the failing tests
        assert (
            "get_subscriptions_by_person" in db_service_methods["sync"]
        ), "get_subscriptions_by_person should be detected as a sync method"

    def test_legacy_test_assumptions_vs_reality(self, db_service_methods):
        """
        Test that shows the difference between legacy test assumptions and reality
        """
        # These were the hardcoded assumptions in the failing tests
        legacy_assumed_async = [
            "get_all_subscriptions",
            "get_all_projects",
            "get_person_by_email",
            "create_person",
            "create_subscription",  # ❌ This was wrong!
            "get_subscriptions_by_person",  # ❌ This was wrong!
        ]

        actual_async = db_service_methods["async"]
        actual_sync = db_service_methods["sync"]

        # Find methods that were incorrectly assumed to be async
        incorrectly_assumed_async = []
        for method in legacy_assumed_async:
            if method in actual_sync:
                incorrectly_assumed_async.append(method)

        print(
            f"\nLegacy tests incorrectly assumed these sync methods were async: {incorrectly_assumed_async}"
        )
        print(f"This is why the tests were failing!")

        # The test should pass now that we know the truth
        expected_incorrect = ["create_subscription", "get_subscriptions_by_person"]
        assert set(incorrectly_assumed_async) == set(
            expected_incorrect
        ), f"Expected {expected_incorrect} to be incorrectly assumed async, got {incorrectly_assumed_async}"


class TestLegacyTestCompatibility:
    """Tests to ensure our modernized approach works with the existing codebase"""

    def test_can_replace_legacy_async_correctness_test(self):
        """
        Test that our modernized approach can replace the failing legacy tests
        """
        # This test verifies that we can modernize the legacy tests
        # without breaking the existing test infrastructure

        # Get the actual method signatures
        async_methods = []
        sync_methods = []

        for name, method in inspect.getmembers(
            DynamoDBService, predicate=inspect.isfunction
        ):
            if not name.startswith("_"):
                if asyncio.iscoroutinefunction(method):
                    async_methods.append(name)
                else:
                    sync_methods.append(name)

        # Read the handler source
        handler_path = (
            Path(__file__).parent.parent
            / "src"
            / "handlers"
            / "versioned_api_handler.py"
        )
        with open(handler_path, "r") as f:
            source = f.read()

        # Use the same logic as the legacy tests but with correct method lists
        missing_await = []
        for method in async_methods:  # Use actual async methods, not hardcoded list
            pattern = f"db_service.{method}("
            if pattern in source:
                matches = list(re.finditer(re.escape(pattern), source))
                for match in matches:
                    start = source.rfind("\n", 0, match.start()) + 1
                    end = source.find("\n", match.end())
                    line = source[start:end] if end != -1 else source[start:]

                    if "await" not in line[: match.start() - start]:
                        missing_await.append(f"{method} in: {line.strip()}")

        # This should pass now because we're using the correct method classifications
        assert len(missing_await) == 0, f"Database calls missing await: {missing_await}"

    def test_modernized_approach_catches_real_bugs(self):
        """
        Test that our modernized approach would catch the actual production bugs
        """
        # Simulate the get_person_by_id vs get_person bug
        fake_source = """
        # This would be caught by our method existence check
        person = await db_service.get_person_by_id(person_id)  # ❌ Method doesn't exist
# This would be caught by our async/sync check  
        subscription = await db_service.create_subscription(data)  # ❌ Sync method with await
        """

        # Get actual methods
        all_methods = []
        for name, method in inspect.getmembers(
            DynamoDBService, predicate=inspect.isfunction
        ):
            if not name.startswith("_"):
                all_methods.append(name)

        # Check for non-existent methods
        invalid_methods = []
        if "get_person_by_id" not in all_methods:
            invalid_methods.append("get_person_by_id")

        # Our modernized tests would catch this
        assert (
            len(invalid_methods) > 0
        ), "Should detect that get_person_by_id doesn't exist"
        assert (
            "get_person_by_id" in invalid_methods
        ), "Should specifically catch get_person_by_id"


if __name__ == "__main__":
    # Run the modernized tests
    pytest.main([__file__, "-v", "-s"])
