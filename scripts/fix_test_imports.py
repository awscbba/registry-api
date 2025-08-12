#!/usr/bin/env python3
"""
Script to fix import issues in test files.
"""

import os
import re


def fix_test_imports():
    """Fix import issues in test files."""

    # Common imports needed for different types of tests
    common_imports = """
import pytest
import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
"""

    model_imports = """
from src.models.person import Person, PersonCreate, PersonUpdate, Address
from src.models.project import Project, ProjectCreate, ProjectUpdate, ProjectStatus
from src.models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionStatus
from src.services.email_service import EmailService
from src.utils.defensive_utils import (
    safe_isoformat, safe_enum_value, safe_datetime_parse,
    safe_field_access, safe_update_expression_builder, safe_model_dump
)
"""

    # Files that need model imports
    files_needing_models = [
        "tests/test_account_locked_until_fix.py",
        "tests/test_address_none_fix.py",
        "tests/test_all_update_inconsistencies.py",
        "tests/test_datetime_field_fixes.py",
        "tests/test_defensive_approach.py",
        "tests/test_enum_fixes.py",
        "tests/test_enum_handling_issue.py",
        "tests/test_subscription_email.py",
    ]

    for file_path in files_needing_models:
        if os.path.exists(file_path):
            print(f"Fixing imports in {file_path}...")
            fix_file_imports(file_path, common_imports + model_imports)

    # Fix async correctness test separately
    fix_async_correctness_test()


def fix_file_imports(file_path, imports_to_add):
    """Fix imports in a single file."""

    with open(file_path, "r") as f:
        content = f.read()

    # Check if imports are already present
    if "from src.models.person import" in content:
        print(f"  ✅ {file_path} already has imports")
        return

    # Find the end of existing imports or the start of the first function
    lines = content.split("\n")
    insert_index = 0

    # Find where to insert imports (after docstring, before first function/class)
    in_docstring = False
    docstring_ended = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Handle docstrings
        if stripped.startswith('"""') and not in_docstring:
            in_docstring = True
            continue
        elif stripped.endswith('"""') and in_docstring:
            in_docstring = False
            docstring_ended = True
            continue
        elif in_docstring:
            continue

        # Skip empty lines after docstring
        if docstring_ended and not stripped:
            continue

        # If we find existing imports, skip them
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue

        # If we find sys.path.insert, skip it
        if "sys.path.insert" in stripped:
            continue

        # Found the insertion point
        if stripped and not stripped.startswith("#"):
            insert_index = i
            break

    # Insert the imports
    lines.insert(insert_index, imports_to_add.strip())

    # Write back
    with open(file_path, "w") as f:
        f.write("\n".join(lines))

    print(f"  ✅ Fixed imports in {file_path}")


def fix_async_correctness_test():
    """Fix the async correctness test specifically."""

    file_path = "tests/test_async_correctness_comprehensive.py"
    if not os.path.exists(file_path):
        return

    print(f"Fixing {file_path}...")

    with open(file_path, "r") as f:
        content = f.read()

    # Add missing imports and fixtures
    additional_content = '''
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
'''

    # Insert after the imports
    lines = content.split("\n")
    insert_index = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("class TestAsyncCorrectness"):
            insert_index = i
            break

    lines.insert(insert_index, additional_content)

    with open(file_path, "w") as f:
        f.write("\n".join(lines))

    print(f"  ✅ Fixed {file_path}")


if __name__ == "__main__":
    print("🔧 Fixing Test Import Issues")
    print("=" * 50)

    fix_test_imports()

    print("\n✅ All import fixes completed!")
    print("Run 'uv run black tests/' to format the files.")
    print("Then run 'pytest tests/ -v' to verify all tests work.")
