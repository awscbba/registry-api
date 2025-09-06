"""Tests for Admin Service - Admin functionality"""

import pytest
from unittest.mock import Mock, patch
from src.services.admin_service import AdminService


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
        mock_people = [Mock(), Mock(), Mock()]
        mock_projects = [Mock(), Mock()]
        mock_subscriptions = [Mock()]

        self.admin_service.people_repository.list_all.return_value = mock_people
        self.admin_service.projects_repository.list_all.return_value = mock_projects
        self.admin_service.subscriptions_repository.list_all.return_value = (
            mock_subscriptions
        )

        # Act
        result = await self.admin_service.get_dashboard_data()

        # Assert
        assert result["total_people"] == 3
        assert result["total_projects"] == 2
        assert result["total_subscriptions"] == 1
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_data_database_error(self):
        """Test dashboard data with database error"""
        # Arrange
        self.admin_service.people_repository.list_all.side_effect = Exception(
            "DB Error"
        )

        # Act & Assert
        with pytest.raises(Exception):
            await self.admin_service.get_dashboard_data()

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

    def test_admin_service_initialization(self):
        """Test admin service initializes correctly"""
        # Act
        service = AdminService()

        # Assert
        assert hasattr(service, "people_repository")
        assert hasattr(service, "projects_repository")
        assert hasattr(service, "subscriptions_repository")
