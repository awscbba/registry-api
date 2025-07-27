"""
Script to run the admin account unlock tests.
"""
import pytest
import sys

if __name__ == "__main__":
    # Run the tests
    result = pytest.main(["-v", "tests/test_admin_account_unlock.py"])
    sys.exit(result)
