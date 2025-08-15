#!/bin/bash
# Script to run tests with email sending disabled

echo "🧪 Running tests with EMAIL_TEST_MODE enabled (no real emails will be sent)"
echo "=================================================================="

# Set the environment variable to disable email sending during tests
export EMAIL_TEST_MODE=true

# Run the tests
if [ "$1" = "all" ]; then
    echo "Running all tests..."
    uv run python -m pytest -v
elif [ "$1" = "critical" ]; then
    echo "Running critical tests..."
    uv run python -m pytest tests/test_critical_integration.py::TestCriticalIntegration::test_api_service_method_consistency tests/test_critical_integration.py::TestCriticalIntegration::test_async_sync_consistency tests/test_critical_integration.py::TestProductionHealthChecks::test_production_api_health -v
elif [ "$1" = "password" ]; then
    echo "Running password-related tests..."
    uv run python -m pytest tests/test_password_reset_service.py tests/test_forgot_password_live.py -v
elif [ -n "$1" ]; then
    echo "Running specific test: $1"
    uv run python -m pytest "$1" -v
else
    echo "Running critical tests by default..."
    uv run python -m pytest tests/test_critical_integration.py::TestCriticalIntegration::test_api_service_method_consistency tests/test_critical_integration.py::TestCriticalIntegration::test_async_sync_consistency tests/test_critical_integration.py::TestProductionHealthChecks::test_production_api_health -v
fi

echo ""
echo "✅ Tests completed with EMAIL_TEST_MODE=true (no real emails sent)"
