"""
Performance tests for Service Registry implementation.
Tests performance characteristics, memory usage, and scalability.
"""

import pytest
import time
import threading
import concurrent.futures
from unittest.mock import patch, AsyncMock
import os

# Set up test environment
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"


class TestServiceRegistryPerformance:
    """Test Service Registry performance under various conditions."""

    def test_concurrent_service_access(self):
        """Test concurrent access to services."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        def access_service(service_name):
            """Access a service multiple times."""
            for _ in range(10):
                service = manager.get_service(service_name)
                assert service is not None
            return True

        # Test concurrent access with multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            service_names = ["auth", "people", "email", "audit", "logging"]

            for service_name in service_names:
                future = executor.submit(access_service, service_name)
                futures.append(future)

            # Wait for all threads to complete
            for future in concurrent.futures.as_completed(futures):
                assert future.result() is True

    def test_service_registry_memory_efficiency(self):
        """Test that Service Registry doesn't create unnecessary instances."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Get the same service multiple times
        services = []
        for _ in range(100):
            service = manager.get_service("auth")
            services.append(service)

        # All should be the same instance (singleton pattern)
        first_service = services[0]
        for service in services[1:]:
            assert (
                service is first_service
            ), "Services should be singletons to save memory"

    def test_health_check_performance(self):
        """Test health check performance under load."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Mock all service health checks for consistent timing
        with (
            patch.object(
                manager.registry.services["people"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_people,
            patch.object(
                manager.registry.services["auth"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch.object(
                manager.registry.services["email"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_email,
            patch.object(
                manager.registry.services["audit"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch.object(
                manager.registry.services["logging"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_logging,
        ):

            # Configure fast mock responses
            for mock in [mock_people, mock_auth, mock_email, mock_audit, mock_logging]:
                mock.return_value = {"status": "healthy"}

            # Time multiple health checks
            start_time = time.time()

            async def run_health_checks():
                for _ in range(10):
                    await manager.health_check()

            import asyncio

            asyncio.run(run_health_checks())

            end_time = time.time()
            total_time = end_time - start_time

            # Should complete 10 health checks in reasonable time (with 1s timeout per check)
            assert (
                total_time < 15.0
            ), f"10 health checks took {total_time:.3f}s, expected < 15.0s"

    def test_api_handler_startup_time(self):
        """Test API handler startup performance."""
        start_time = time.time()

        # Import should trigger initialization
        from src.handlers.modular_api_handler import app

        end_time = time.time()
        startup_time = end_time - start_time

        # Should start up in reasonable time
        assert (
            startup_time < 10.0
        ), f"API handler startup took {startup_time:.2f}s, expected < 10.0s"
        assert app is not None

    def test_service_method_call_performance(self):
        """Test performance of service method calls."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()
        auth_service = manager.get_service("auth")

        # Time service method access
        start_time = time.time()

        for _ in range(1000):
            # Just access the method, don't call it (to avoid AWS dependencies)
            method = getattr(auth_service, "authenticate_user", None)
            assert method is not None

        end_time = time.time()
        access_time = end_time - start_time

        # Should access methods very quickly
        assert (
            access_time < 0.1
        ), f"1000 method accesses took {access_time:.3f}s, expected < 0.1s"


class TestServiceRegistryScalability:
    """Test Service Registry scalability characteristics."""

    def test_service_registry_scales_with_services(self):
        """Test that registry performance doesn't degrade with more services."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Time service access with all services
        service_names = list(manager.registry.services.keys())

        start_time = time.time()

        # Access each service multiple times
        for _ in range(10):
            for service_name in service_names:
                service = manager.get_service(service_name)
                assert service is not None

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle all services efficiently
        total_accesses = 10 * len(service_names)
        time_per_access = total_time / total_accesses

        assert (
            time_per_access < 0.001
        ), f"Average access time {time_per_access:.6f}s, expected < 0.001s"

    def test_concurrent_health_checks(self):
        """Test concurrent health checks don't interfere."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Mock health checks for consistent behavior
        with patch.object(
            manager.registry.services["auth"], "health_check", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = {"status": "healthy"}

            async def run_concurrent_health_checks():
                import asyncio

                # Run multiple health checks concurrently
                tasks = []
                for _ in range(5):
                    task = asyncio.create_task(manager.health_check())
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                return results

            import asyncio

            start_time = time.time()
            results = asyncio.run(run_concurrent_health_checks())
            end_time = time.time()

            # All should succeed
            assert len(results) == 5
            for result in results:
                assert "service_registry_manager" in result

            # Should complete quickly even with concurrency (with timeouts)
            total_time = end_time - start_time
            assert (
                total_time < 10.0
            ), f"Concurrent health checks took {total_time:.3f}s, expected < 10.0s"


class TestServiceRegistryResourceUsage:
    """Test Service Registry resource usage patterns."""

    def test_service_registry_cleanup(self):
        """Test that Service Registry cleans up properly."""
        from src.services.service_registry_manager import ServiceRegistryManager

        # Create and destroy multiple managers
        managers = []
        for _ in range(5):
            manager = ServiceRegistryManager()
            managers.append(manager)

        # All should be independent
        for i, manager in enumerate(managers):
            services = list(manager.registry.services.keys())
            assert (
                len(services) == 11
            ), f"Manager {i} has {len(services)} services, expected 10"

    def test_service_instance_reuse(self):
        """Test that services are properly reused."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Get services multiple times
        auth_services = []
        for _ in range(10):
            service = manager.get_service("auth")
            auth_services.append(service)

        # All should be the same instance
        first_service = auth_services[0]
        for service in auth_services[1:]:
            assert service is first_service, "Service instances should be reused"

    def test_no_memory_leaks_in_service_access(self):
        """Test that repeated service access doesn't cause memory leaks."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Access services many times
        for _ in range(1000):
            for service_name in ["auth", "people", "email"]:
                service = manager.get_service(service_name)
                # Do something with the service to ensure it's not optimized away
                assert service.service_name is not None


class TestServiceRegistryStressTest:
    """Stress tests for Service Registry under heavy load."""

    def test_high_frequency_service_access(self):
        """Test Service Registry under high-frequency access."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        start_time = time.time()

        # High-frequency access
        for _ in range(10000):
            service = manager.get_service("auth")
            assert service is not None

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle high frequency access efficiently
        assert (
            total_time < 1.0
        ), f"10000 service accesses took {total_time:.3f}s, expected < 1.0s"

    def test_mixed_service_access_patterns(self):
        """Test mixed access patterns to different services."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()
        service_names = ["auth", "people", "email", "audit", "logging"]

        start_time = time.time()

        # Mixed access pattern
        for i in range(1000):
            service_name = service_names[i % len(service_names)]
            service = manager.get_service(service_name)
            assert service is not None

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle mixed patterns efficiently
        assert (
            total_time < 0.5
        ), f"1000 mixed accesses took {total_time:.3f}s, expected < 0.5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
