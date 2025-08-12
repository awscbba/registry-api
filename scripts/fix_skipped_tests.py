#!/usr/bin/env python3
"""
Script to fix all skipped tests by converting them to proper pytest tests.
"""

import os
import re
from pathlib import Path


def fix_async_test_functions():
    """Fix async test functions that are missing pytest.mark.asyncio decorator."""

    test_files = [
        "tests/test_email.py",
        "tests/test_enum_fixes.py",
        "tests/test_datetime_field_fixes.py",
        "tests/test_address_none_fix.py",
        "tests/test_account_locked_until_fix.py",
        "tests/test_all_update_inconsistencies.py",
        "tests/test_defensive_approach.py",
        "tests/test_enum_handling_issue.py",
        "tests/test_subscription_email.py",
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Fixing {test_file}...")
            fix_single_test_file(test_file)


def fix_single_test_file(file_path):
    """Fix a single test file."""

    with open(file_path, "r") as f:
        content = f.read()

    # Check if it's a script-style test (has if __name__ == "__main__")
    if 'if __name__ == "__main__"' in content:
        content = convert_script_to_pytest(content, file_path)
    else:
        # Just add missing pytest.mark.asyncio decorators
        content = add_asyncio_decorators(content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"  ✅ Fixed {file_path}")


def convert_script_to_pytest(content, file_path):
    """Convert a script-style test to proper pytest format."""

    # Extract the main async function
    main_func_match = re.search(
        r"async def (test_\w+)\(\):(.*?)(?=\n\nif __name__|$)", content, re.DOTALL
    )

    if not main_func_match:
        print(f"  ⚠️  Could not find main test function in {file_path}")
        return content

    func_name = main_func_match.group(1)
    func_body = main_func_match.group(2)

    # Create proper pytest test
    pytest_content = f'''"""
Test module converted from script format.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.mark.asyncio
async def {func_name}():
    """Test function converted from script format."""{func_body}


# Keep the original script functionality for backward compatibility
if __name__ == "__main__":
    asyncio.run({func_name}())
'''

    return pytest_content


def add_asyncio_decorators(content):
    """Add @pytest.mark.asyncio decorators to async test functions."""

    # Find async def test_ functions that don't have the decorator
    pattern = r"((?:^|\n)(?!.*@pytest\.mark\.asyncio))(async def test_\w+\([^)]*\):)"

    def add_decorator(match):
        prefix = match.group(1)
        func_def = match.group(2)

        # Add the decorator
        if prefix.strip():
            return f"{prefix}@pytest.mark.asyncio\n{func_def}"
        else:
            return f"@pytest.mark.asyncio\n{func_def}"

    content = re.sub(pattern, add_decorator, content, flags=re.MULTILINE)

    # Ensure pytest is imported
    if "@pytest.mark.asyncio" in content and "import pytest" not in content:
        # Add import after existing imports
        import_pattern = r"((?:^import .*\n|^from .* import .*\n)+)"
        if re.search(import_pattern, content, re.MULTILINE):
            content = re.sub(
                import_pattern,
                r"\1import pytest\n",
                content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            content = "import pytest\n" + content

    return content


def fix_return_statements_in_tests():
    """Fix test functions that return values instead of using assert."""

    test_files = [
        "tests/test_email_simple.py",
        "tests/test_person_update_api_real.py",
        "tests/test_project_subscription_api.py",
        "tests/test_subscription_creation.py",
        "tests/test_xray.py",
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Fixing return statements in {test_file}...")
            fix_return_statements(test_file)


def fix_return_statements(file_path):
    """Fix return statements in test functions."""

    with open(file_path, "r") as f:
        content = f.read()

    # Replace return True/False with assert statements
    content = re.sub(r"return True", "assert True", content)
    content = re.sub(r"return False", "assert False", content)

    # Replace other return statements with assertions
    content = re.sub(r"return (.+)", r"assert \1", content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"  ✅ Fixed return statements in {file_path}")


if __name__ == "__main__":
    print("🔧 Fixing Skipped Tests")
    print("=" * 50)

    print("\n1. Fixing async test functions...")
    fix_async_test_functions()

    print("\n2. Fixing return statements in tests...")
    fix_return_statements_in_tests()

    print("\n✅ All test fixes completed!")
    print("\nRun 'pytest tests/ -v' to verify all tests are now working.")
