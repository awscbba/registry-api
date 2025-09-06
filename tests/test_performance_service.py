"""Tests for Performance Service - Critical service with 0% coverage"""

import pytest
from unittest.mock import Mock, patch
from src.services.performance_service import PerformanceService


class TestPerformanceService:
    """Test Performance Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.performance_service = PerformanceService()

    @pytest.mark.asyncio
    async def test_get_health_status_success(self):
        """Test getting health status successfully"""
        # Arrange
        mock_metrics = Mock()
        mock_metrics.response_time_avg = 150.0
        mock_metrics.memory_usage_mb = 512.0
        mock_metrics.cpu_usage_percent = 45.0

        mock_components = {
            "database": {"status": "healthy", "response_time": 50},
            "cache": {"status": "healthy", "response_time": 10},
        }

        with (
            patch.object(
                self.performance_service,
                "_collect_system_metrics",
                return_value=mock_metrics,
            ),
            patch.object(
                self.performance_service,
                "_check_component_health",
                return_value=mock_components,
            ),
        ):

            # Act
            result = await self.performance_service.get_health_status()

            # Assert
            assert result["status"] == "healthy"
            assert result["metrics"]["response_time_avg"] == 150.0
            assert result["components"] == mock_components
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_collect_system_metrics_success(self):
        """Test collecting system metrics"""
        # Act
        result = await self.performance_service._collect_system_metrics()

        # Assert
        assert hasattr(result, "response_time_avg")
        assert hasattr(result, "memory_usage_mb")
        assert hasattr(result, "cpu_usage_percent")
        assert result.response_time_avg >= 0
        assert result.memory_usage_mb >= 0
        assert result.cpu_usage_percent >= 0

    @pytest.mark.asyncio
    async def test_check_component_health_success(self):
        """Test checking component health"""
        # Arrange
        mock_repo = Mock()
        mock_repo.health_check.return_value = True

        with (
            patch(
                "src.repositories.people_repository.PeopleRepository",
                return_value=mock_repo,
            ),
            patch(
                "src.repositories.projects_repository.ProjectsRepository",
                return_value=mock_repo,
            ),
        ):

            # Act
            result = await self.performance_service._check_component_health()

            # Assert
            assert isinstance(result, dict)
            assert len(result) > 0

            # Check that components have required fields
            for component_name, component_data in result.items():
                assert "status" in component_data
                assert "response_time" in component_data

    @pytest.mark.asyncio
    async def test_check_repository_health_success(self):
        """Test checking individual repository health"""
        # Arrange
        mock_repo = Mock()
        mock_repo.health_check.return_value = True

        # Act
        result = await self.performance_service._check_repository_health(
            mock_repo, "test_repo"
        )

        # Assert
        assert result["status"] == "healthy"
        assert result["response_time"] >= 0
        mock_repo.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_repository_health_failure(self):
        """Test repository health check failure"""
        # Arrange
        mock_repo = Mock()
        mock_repo.health_check.side_effect = Exception("Connection failed")

        # Act
        result = await self.performance_service._check_repository_health(
            mock_repo, "test_repo"
        )

        # Assert
        assert result["status"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_performance_stats_success(self):
        """Test getting performance statistics"""
        # Arrange
        self.performance_service._request_count = 100
        self.performance_service._total_response_time = 5000.0

        # Act
        result = await self.performance_service.get_performance_stats()

        # Assert
        assert result["request_count"] == 100
        assert result["average_response_time"] == 50.0  # 5000/100
        assert "uptime_seconds" in result
        assert "timestamp" in result

    def test_record_request_success(self):
        """Test recording request metrics"""
        # Arrange
        initial_count = self.performance_service._request_count
        initial_time = self.performance_service._total_response_time

        # Act
        self.performance_service.record_request(150.0)

        # Assert
        assert self.performance_service._request_count == initial_count + 1
        assert self.performance_service._total_response_time == initial_time + 150.0

    def test_performance_service_initialization(self):
        """Test performance service initializes correctly"""
        # Act
        service = PerformanceService()

        # Assert
        assert service._request_count == 0
        assert service._total_response_time == 0.0
        assert hasattr(service, "_start_time")

    @pytest.mark.asyncio
    async def test_health_status_with_unhealthy_components(self):
        """Test health status when components are unhealthy"""
        # Arrange
        mock_metrics = Mock()
        mock_metrics.response_time_avg = 150.0

        mock_components = {
            "database": {"status": "unhealthy", "error": "Connection timeout"},
            "cache": {"status": "healthy", "response_time": 10},
        }

        with (
            patch.object(
                self.performance_service,
                "_collect_system_metrics",
                return_value=mock_metrics,
            ),
            patch.object(
                self.performance_service,
                "_check_component_health",
                return_value=mock_components,
            ),
        ):

            # Act
            result = await self.performance_service.get_health_status()

            # Assert
            assert (
                result["status"] == "degraded"
            )  # Should be degraded when some components unhealthy
            assert result["components"]["database"]["status"] == "unhealthy"
