#!/usr/bin/env python3
"""
Test runner for versioned API handler tests.

This script runs the comprehensive test suite for the versioned API handler
and provides detailed reporting on test results.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run the versioned API handler tests"""

    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("🧪 Running Versioned API Handler Test Suite")
    print("=" * 50)

    # Test files to run
    test_files = [
        "tests/test_versioned_api_handler.py",
        "tests/test_async_correctness.py",
    ]

    # Check if test files exist
    missing_files = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing_files.append(test_file)

    if missing_files:
        print(f"❌ Missing test files: {missing_files}")
        return False

    # Run tests with different configurations
    test_configs = [
        {"name": "Unit Tests", "args": ["-v", "-m", "unit", "--tb=short"]},
        {"name": "Async Tests", "args": ["-v", "-m", "async_test", "--tb=short"]},
        {
            "name": "Integration Tests",
            "args": ["-v", "-m", "integration", "--tb=short"],
        },
        {
            "name": "All Tests with Coverage",
            "args": [
                "-v",
                "--cov=src/handlers",
                "--cov-report=term-missing",
                "--tb=short",
            ],
        },
    ]

    all_passed = True

    for config in test_configs:
        print(f"\n🔍 Running {config['name']}")
        print("-" * 30)

        cmd = ["python", "-m", "pytest"] + config["args"] + test_files

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"✅ {config['name']} PASSED")
                if result.stdout:
                    # Show summary line
                    lines = result.stdout.strip().split("\n")
                    summary_lines = [
                        line
                        for line in lines
                        if "passed" in line
                        and ("failed" in line or "error" in line or "warnings" in line)
                    ]
                    if summary_lines:
                        print(f"   {summary_lines[-1]}")
            else:
                print(f"❌ {config['name']} FAILED")
                all_passed = False
                if result.stdout:
                    print("STDOUT:")
                    print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)

        except subprocess.TimeoutExpired:
            print(f"⏰ {config['name']} TIMED OUT")
            all_passed = False
        except Exception as e:
            print(f"💥 {config['name']} ERROR: {e}")
            all_passed = False

    # Run specific critical tests
    print(f"\n🎯 Running Critical Tests")
    print("-" * 30)

    critical_tests = [
        "test_versioned_api_handler.py::TestVersionedAPIHandler::test_no_duplicate_routes",
        "test_versioned_api_handler.py::TestVersionedAPIHandler::test_all_routes_registered",
        "test_async_correctness.py::TestAsyncCorrectness::test_all_endpoint_functions_are_async",
        "test_async_correctness.py::TestAsyncCorrectness::test_database_calls_are_awaited",
        "test_async_correctness.py::TestAsyncCorrectness::test_no_duplicate_function_definitions",
    ]

    for test in critical_tests:
        cmd = ["python", "-m", "pytest", f"tests/{test}", "-v"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            test_name = test.split("::")[-1]
            if result.returncode == 0:
                print(f"✅ {test_name}")
            else:
                print(f"❌ {test_name}")
                all_passed = False
                if result.stdout:
                    print(f"   {result.stdout.strip()}")
        except Exception as e:
            print(f"💥 {test_name}: {e}")
            all_passed = False

    # Final summary
    print(f"\n{'=' * 50}")
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Versioned API Handler is ready for deployment")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please fix the issues before deployment")

    return all_passed


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        "pytest",
        "pytest-cov",
        "pytest-asyncio",
        "fastapi",
        "httpx",  # Required by TestClient
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {missing_packages}")
        print(f"💡 Install with: pip install {' '.join(missing_packages)}")
        return False

    return True


def main():
    """Main function"""
    print("🚀 Versioned API Handler Test Runner")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Run tests
    success = run_tests()

    if success:
        print(f"\n🎯 Next Steps:")
        print("1. Commit your changes")
        print("2. Create a pull request")
        print("3. Deploy to staging/production")
        sys.exit(0)
    else:
        print(f"\n🔧 Fix the failing tests and run again")
        sys.exit(1)


if __name__ == "__main__":
    main()
