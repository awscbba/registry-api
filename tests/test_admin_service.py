"""Tests for Admin Service - Critical service with 0% coverage"""

import pytest
from unittest.mock import Mock, patch
from src.services.admin_service import AdminService
from src.exceptions.base_exceptions import DatabaseException


class TestAdminService:
    """Test Admin Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.admin_service = AdminService()
        self.admin_service.people_repository = Mock()
        self.admin_service.projects_repository = Mock()
        self.admin_service.subscriptions_repository = Mock()

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self):
        """Test getting dashboard data successfully"""
        # Arrange
        self.admin_service.people_repository.count_all.return_value = 100
        self.admin_service.projects_repository.count_all.return_value = 25
        self.admin_service.subscriptions_repository.count_all.return_value = 150

        # Act
        result = await self.admin_service.get_dashboard_data()

        # Assert
        assert result["total_people"] == 100
        assert result["total_projects"] == 25
        assert result["total_subscriptions"] == 150
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_data_database_error(self):
        """Test dashboard data with database error"""
        # Arrange
        self.admin_service.people_repository.count_all.side_effect = Exception(
            "DB Error"
        )

        # Act & Assert
        with pytest.raises(DatabaseException) as exc_info:
            await self.admin_service.get_dashboard_data()

        assert "get_dashboard_data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_enhanced_dashboard_data_success(self):
        """Test getting enhanced dashboard data"""
        # Arrange - Mock basic dashboard data
        basic_data = {
            "total_people": 100,
            "total_projects": 25,
            "total_subscriptions": 150,
            "timestamp": "2025-01-01T00:00:00Z",
        }

        with patch.object(
            self.admin_service, "get_dashboard_data", return_value=basic_data
        ):
            self.admin_service.subscriptions_repository.get_recent_subscriptions.return_value = [
                {"id": "sub1", "created_at": "2025-01-01"},
                {"id": "sub2", "created_at": "2025-01-02"},
            ]
            self.admin_service.projects_repository.get_active_projects.return_value = [
                {"id": "proj1", "status": "active"}
            ]

            # Act
            result = await self.admin_service.get_enhanced_dashboard_data()

            # Assert
            assert result["basic_stats"] == basic_data
            assert result["recent_subscriptions_count"] == 2
            assert result["active_projects_count"] == 1
            assert "analytics" in result

    @pytest.mark.asyncio
    async def test_get_enhanced_dashboard_data_partial_failure(self):
        """Test enhanced dashboard with partial data failure"""
        # Arrange
        basic_data = {"total_people": 100}

        with patch.object(
            self.admin_service, "get_dashboard_data", return_value=basic_data
        ):
            # Simulate failure in getting recent subscriptions
            self.admin_service.subscriptions_repository.get_recent_subscriptions.side_effect = Exception(
                "Error"
            )
            self.admin_service.projects_repository.get_active_projects.return_value = []

            # Act
            result = await self.admin_service.get_enhanced_dashboard_data()

            # Assert
            assert result["basic_stats"] == basic_data
            assert (
                result["recent_subscriptions_count"] == 0
            )  # Should default to 0 on error
            assert result["active_projects_count"] == 0

    def test_admin_service_initialization(self):
        """Test admin service initializes correctly"""
        # Act
        service = AdminService()

        # Assert
        assert hasattr(service, "people_repository")
        assert hasattr(service, "projects_repository")
        assert hasattr(service, "subscriptions_repository")

    @pytest.mark.asyncio
    async def test_dashboard_data_structure(self):
        """Test dashboard data has correct structure"""
        # Arrange
        self.admin_service.people_repository.count_all.return_value = 50
        self.admin_service.projects_repository.count_all.return_value = 10
        self.admin_service.subscriptions_repository.count_all.return_value = 75

        # Act
        result = await self.admin_service.get_dashboard_data()

        # Assert
        required_fields = [
            "total_people",
            "total_projects",
            "total_subscriptions",
            "timestamp",
        ]
        for field in required_fields:
            assert field in result

        # Verify data types
        assert isinstance(result["total_people"], int)
        assert isinstance(result["total_projects"], int)
        assert isinstance(result["total_subscriptions"], int)
        assert isinstance(result["timestamp"], str)
