"""
Test for startup health check fix - ensures Lambda doesn't shut down on health check failures.

This test verifies that the fix for the 'dict' object has no attribute 'status' error
prevents Lambda startup failures and allows the system to continue processing requests.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.health_check_utils import convert_health_check, is_healthy
from src.core.base_service import HealthCheck, ServiceStatus


class TestStartupHealthCheckFix:
    """Test the startup health check fix that prevents Lambda shutdown."""

    def test_convert_health_check_with_dict_response(self):
        """Test that convert_health_check handles dictionary responses correctly."""
        # Simulate a service returning a dictionary (the problematic case)
        dict_health = {
            "service_name": "test_service",
            "status": "healthy",
            "healthy": True,
            "message": "Service is running",
            "details": {"connections": 5},
            "response_time_ms": 45,
        }

        result = convert_health_check(dict_health)

        assert result["service_name"] == "test_service"
        assert result["status"] == "healthy"
        assert result["healthy"] is True
        assert result["message"] == "Service is running"
        assert result["details"]["connections"] == 5
        assert result["response_time_ms"] == 45

    def test_convert_health_check_with_object_response(self):
        """Test that convert_health_check handles HealthCheck objects correctly."""
        # Simulate a service returning a HealthCheck object
        health_obj = HealthCheck(
            service_name="test_service",
            status=ServiceStatus.HEALTHY,
            message="Service is running",
            details={"connections": 5},
            response_time_ms=45,
        )

        result = convert_health_check(health_obj)

        assert result["service_name"] == "test_service"
        assert result["status"] == "healthy"
        assert result["healthy"] is True
        assert result["message"] == "Service is running"
        assert result["details"]["connections"] == 5
        assert result["response_time_ms"] == 45

    def test_is_healthy_with_dict_response(self):
        """Test that is_healthy correctly identifies healthy dictionary responses."""
        healthy_dict = {"status": "healthy", "healthy": True}
        unhealthy_dict = {"status": "unhealthy", "healthy": False}
        status_only_dict = {"status": "healthy"}

        assert is_healthy(healthy_dict) is True
        assert is_healthy(unhealthy_dict) is False
        assert is_healthy(status_only_dict) is True

    def test_is_healthy_with_object_response(self):
        """Test that is_healthy correctly identifies healthy HealthCheck objects."""
        healthy_obj = HealthCheck(
            service_name="test", status=ServiceStatus.HEALTHY, message="OK"
        )
        unhealthy_obj = HealthCheck(
            service_name="test", status=ServiceStatus.UNHEALTHY, message="Error"
        )

        assert is_healthy(healthy_obj) is True
        assert is_healthy(unhealthy_obj) is False

    def test_convert_health_check_with_unknown_format(self):
        """Test that convert_health_check handles unknown formats safely."""
        unknown_format = "invalid_health_check"

        result = convert_health_check(unknown_format)

        assert result["service_name"] == "unknown"
        assert result["status"] == "unknown"
        assert result["healthy"] is False
        assert "Unknown health check format" in result["message"]

    @pytest.mark.asyncio
    async def test_startup_health_check_no_longer_crashes(self):
        """Test that startup health checks don't crash with mixed response formats."""
        # Mock service registry with services returning different response formats
        mock_service_1 = AsyncMock()
        mock_service_1.health_check.return_value = {
            "status": "healthy",
            "healthy": True,
            "message": "Dict response",
        }

        mock_service_2 = AsyncMock()
        mock_service_2.health_check.return_value = HealthCheck(
            service_name="service_2",
            status=ServiceStatus.HEALTHY,
            message="Object response",
        )

        mock_service_3 = AsyncMock()
        mock_service_3.health_check.return_value = {
            "status": "unhealthy",
            "healthy": False,
            "message": "Unhealthy dict response",
        }

        # Mock the service registry
        mock_registry = MagicMock()
        mock_registry.services.keys.return_value = [
            "service_1",
            "service_2",
            "service_3",
        ]
        mock_registry.get_service.side_effect = lambda name: {
            "service_1": mock_service_1,
            "service_2": mock_service_2,
            "service_3": mock_service_3,
        }[name]

        # Simulate the startup health check logic (the fixed version)
        health_results = []
        try:
            for service_name in mock_registry.services.keys():
                service = mock_registry.get_service(service_name)
                health = await service.health_check()

                # Use the safe converter (this is the fix)
                health_dict = convert_health_check(health)
                service_is_healthy = is_healthy(health)
                health_status = health_dict.get("status", "unknown")

                health_results.append(
                    {
                        "service": service_name,
                        "status": health_status,
                        "healthy": service_is_healthy,
                    }
                )

            # Verify all services were processed without crashing
            assert len(health_results) == 3
            assert health_results[0]["service"] == "service_1"
            assert health_results[0]["healthy"] is True
            assert health_results[1]["service"] == "service_2"
            assert health_results[1]["healthy"] is True
            assert health_results[2]["service"] == "service_3"
            assert health_results[2]["healthy"] is False

        except Exception as e:
            pytest.fail(f"Startup health check should not crash: {e}")

    def test_health_check_fix_prevents_attribute_error(self):
        """Test that the fix prevents the specific 'dict' object has no attribute 'status' error."""
        # This is the exact scenario that was causing the Lambda shutdown
        problematic_dict = {
            "service_name": "problematic_service",
            "status": "healthy",
            "message": "This used to cause AttributeError",
        }

        # The old code would try: problematic_dict.status (AttributeError)
        # The new code uses: convert_health_check(problematic_dict)
        try:
            # This should NOT raise an AttributeError
            result = convert_health_check(problematic_dict)
            healthy = is_healthy(problematic_dict)

            assert result["status"] == "healthy"
            assert healthy is True

        except AttributeError as e:
            pytest.fail(f"Health check fix should prevent AttributeError: {e}")

    def test_health_check_fix_maintains_backward_compatibility(self):
        """Test that the fix maintains compatibility with existing HealthCheck objects."""
        # Ensure existing HealthCheck objects still work correctly
        health_obj = HealthCheck(
            service_name="backward_compat_test",
            status=ServiceStatus.HEALTHY,
            message="Backward compatibility test",
            details={"test": True},
            response_time_ms=25,
        )

        result = convert_health_check(health_obj)
        healthy = is_healthy(health_obj)

        assert result["service_name"] == "backward_compat_test"
        assert result["status"] == "healthy"
        assert result["healthy"] is True
        assert result["message"] == "Backward compatibility test"
        assert result["details"]["test"] is True
        assert result["response_time_ms"] == 25
        assert healthy is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
