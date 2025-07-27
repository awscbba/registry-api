"""
Test runner script for person operations.
"""
import os
import sys
import pytest

if __name__ == "__main__":
    # Add the src directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    # Run the tests
    test_files = [
        "tests/test_person_validation_service.py",
        "tests/test_person_endpoints_integration.py",
        "tests/test_secure_endpoints.py",
        "tests/test_comprehensive_validation.py"
    ]

    # Print test summary
    print("Running comprehensive test suite for person operations:")
    print("1. Person validation service tests")
    print("2. Person endpoints integration tests")
    print("3. Security and authorization tests")
    print("4. Comprehensive validation rule tests")
    print("\nTotal test files: 4\n")

    # Run the tests
    pytest.main(["-v"] + test_files)
