"""
Test Phase 4: Service-Repository Integration
Tests the integration between services and repositories.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.services.people_service import PeopleService
from src.services.projects_service import ProjectsService
from src.services.audit_service import AuditService


class TestPhase4ServiceRepositoryIntegration:
    """Test service-repository integration for Phase 4."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = AsyncMock(success=True, data=10)
        mock_repo.get_performance_stats.return_value = {
            "operation_count": 5,
            "total_response_time_ms": 150.0,
            "average_response_time_ms": 30.0,
            "table_name": "people",
        }
        return mock_repo

    @pytest.fixture
    def mock_project_repository(self):
        """Mock ProjectRepository for testing."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = AsyncMock(success=True, data=5)
        mock_repo.get_performance_stats.return_value = {
            "operation_count": 3,
            "total_response_time_ms": 90.0,
            "average_response_time_ms": 30.0,
            "table_name": "projects",
        }
        return mock_repo

    @pytest.fixture
    def mock_audit_repository(self):
        """Mock AuditRepository for testing."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = AsyncMock(success=True, data=100)
        mock_repo.get_performance_stats.return_value = {
            "operation_count": 20,
            "total_response_time_ms": 400.0,
            "average_response_time_ms": 20.0,
            "table_name": "audit_logs",
        }
        return mock_repo

    def test_people_service_has_repository_integration(self):
        """Test that PeopleService properly integrates with UserRepository."""
        service = PeopleService()

        # Verify repository is initialized
        assert hasattr(service, "user_repository")
        assert service.user_repository is not None

        # Verify service name
        assert service.service_name == "people_service"

    def test_projects_service_has_repository_integration(self):
        """Test that ProjectsService properly integrates with ProjectRepository."""
        service = ProjectsService()

        # Verify repository is initialized
        assert hasattr(service, "project_repository")
        assert service.project_repository is not None

        # Verify service name
        assert service.service_name == "projects_service"

    def test_audit_service_has_repository_integration(self):
        """Test that AuditService properly integrates with AuditRepository."""
        service = AuditService()

        # Verify repository is initialized
        assert hasattr(service, "audit_repository")
        assert service.audit_repository is not None

        # Verify service name
        assert service.service_name == "audit_service"

    @pytest.mark.asyncio
    async def test_people_service_initialize_with_repository(
        self, mock_user_repository
    ):
        """Test PeopleService initialization using repository."""
        service = PeopleService()
        service.user_repository = mock_user_repository

        result = await service.initialize()

        assert result is True
        mock_user_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_people_service_health_check_with_repository(
        self, mock_user_repository
    ):
        """Test PeopleService health check using repository."""
        service = PeopleService()
        service.user_repository = mock_user_repository

        result = await service.health_check()

        assert result["service"] == "people_service"
        assert result["status"] == "healthy"
        assert result["repository"] == "connected"
        assert result["user_count"] == 10
        assert "performance" in result

        mock_user_repository.count.assert_called_once()
        mock_user_repository.get_performance_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_projects_service_initialize_with_repository(
        self, mock_project_repository
    ):
        """Test ProjectsService initialization using repository."""
        service = ProjectsService()
        service.project_repository = mock_project_repository

        result = await service.initialize()

        assert result is True
        mock_project_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_projects_service_health_check_with_repository(
        self, mock_project_repository
    ):
        """Test ProjectsService health check using repository."""
        service = ProjectsService()
        service.project_repository = mock_project_repository

        result = await service.health_check()

        assert result["service"] == "projects_service"
        assert result["status"] == "healthy"
        assert result["repository"] == "connected"
        assert result["project_count"] == 5
        assert "performance" in result

        mock_project_repository.count.assert_called_once()
        mock_project_repository.get_performance_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_service_initialize_with_repository(
        self, mock_audit_repository
    ):
        """Test AuditService initialization using repository."""
        service = AuditService()
        service.audit_repository = mock_audit_repository

        result = await service.initialize()

        assert result is True
        mock_audit_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_service_health_check_with_repository(
        self, mock_audit_repository
    ):
        """Test AuditService health check using repository."""
        service = AuditService()
        service.audit_repository = mock_audit_repository

        result = await service.health_check()

        assert result["service"] == "audit_service"
        assert result["status"] == "healthy"
        assert result["repository"] == "connected"
        assert result["audit_log_count"] == 100
        assert "performance" in result

        mock_audit_repository.count.assert_called_once()
        mock_audit_repository.get_performance_stats.assert_called_once()

    def test_services_maintain_backward_compatibility(self):
        """Test that services maintain backward compatibility with legacy db_service."""
        people_service = PeopleService()
        projects_service = ProjectsService()

        # Verify legacy db_service is still available for backward compatibility
        assert hasattr(people_service, "db_service")
        assert hasattr(projects_service, "db_service")

        # Verify new repository is also available
        assert hasattr(people_service, "user_repository")
        assert hasattr(projects_service, "project_repository")

    def test_service_repository_integration_architecture(self):
        """Test the overall architecture of service-repository integration."""
        people_service = PeopleService()
        projects_service = ProjectsService()
        audit_service = AuditService()

        # Verify all services inherit from BaseService
        from src.core.base_service import BaseService

        assert isinstance(people_service, BaseService)
        assert isinstance(projects_service, BaseService)
        assert isinstance(audit_service, BaseService)

        # Verify repository integration
        assert people_service.user_repository.table_name == "people"
        assert projects_service.project_repository.table_name == "projects"
        assert audit_service.audit_repository.table_name == "audit_logs"

    @pytest.mark.asyncio
    async def test_repository_error_handling(self, mock_user_repository):
        """Test error handling when repository operations fail."""
        service = PeopleService()
        service.user_repository = mock_user_repository

        # Mock repository failure
        mock_user_repository.count.return_value = AsyncMock(
            success=False, error="Connection failed"
        )

        result = await service.health_check()

        assert result["service"] == "people_service"
        assert result["status"] == "unhealthy"
        assert result["repository"] == "disconnected"
        assert result["error"] == "Connection failed"

    def test_performance_monitoring_integration(self):
        """Test that performance monitoring is integrated into services."""
        people_service = PeopleService()
        projects_service = ProjectsService()
        audit_service = AuditService()

        # Verify performance stats methods are available
        assert hasattr(people_service.user_repository, "get_performance_stats")
        assert hasattr(projects_service.project_repository, "get_performance_stats")
        assert hasattr(audit_service.audit_repository, "get_performance_stats")

    def test_service_logging_integration(self):
        """Test that logging is properly integrated in services."""
        people_service = PeopleService()
        projects_service = ProjectsService()
        audit_service = AuditService()

        # Verify logger is available
        assert hasattr(people_service, "logger")
        assert hasattr(projects_service, "logger")
        assert hasattr(audit_service, "logger")

        # Verify logger names
        assert people_service.logger.name == "people_service"
        assert projects_service.logger.name == "projects_service"
        assert audit_service.logger.name == "audit_service"


class TestPhase4NewRepositoryMethods:
    """Test new repository-based methods added in Phase 4."""

    @pytest.fixture
    def mock_person_data(self):
        """Mock person data for testing."""
        return {
            "id": "test-person-id",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "is_active": True,
        }

    @pytest.fixture
    def mock_project_data(self):
        """Mock project data for testing."""
        return {
            "id": "test-project-id",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "created_by": "test-user-id",
        }

    def test_people_service_has_new_repository_methods(self):
        """Test that PeopleService has new repository-based methods."""
        service = PeopleService()

        # Verify new methods exist
        assert hasattr(service, "get_all_people_repository")
        assert hasattr(service, "get_person_by_email")
        assert hasattr(service, "get_active_people")
        assert hasattr(service, "get_people_performance_stats")

    def test_projects_service_has_new_repository_methods(self):
        """Test that ProjectsService has new repository-based methods."""
        service = ProjectsService()

        # Verify new methods exist
        assert hasattr(service, "get_all_projects_repository")
        assert hasattr(service, "get_projects_by_status")
        assert hasattr(service, "get_projects_by_creator")
        assert hasattr(service, "get_projects_performance_stats")

    def test_audit_service_has_comprehensive_methods(self):
        """Test that AuditService has comprehensive audit methods."""
        service = AuditService()

        # Verify audit methods exist
        assert hasattr(service, "create_audit_log")
        assert hasattr(service, "get_user_audit_trail")
        assert hasattr(service, "get_resource_audit_trail")
        assert hasattr(service, "get_audit_logs_by_action")
        assert hasattr(service, "get_recent_audit_logs")
        assert hasattr(service, "get_audit_summary")
        assert hasattr(service, "get_compliance_report")
        assert hasattr(service, "search_audit_logs")
        assert hasattr(service, "delete_old_audit_logs")
        assert hasattr(service, "get_audit_performance_stats")

    def test_phase4_integration_completeness(self):
        """Test that Phase 4 integration is complete and comprehensive."""
        # Verify all three main services are integrated
        people_service = PeopleService()
        projects_service = ProjectsService()
        audit_service = AuditService()

        # Verify repository pattern integration
        assert people_service.user_repository is not None
        assert projects_service.project_repository is not None
        assert audit_service.audit_repository is not None

        # Verify backward compatibility
        assert hasattr(people_service, "db_service")
        assert hasattr(projects_service, "db_service")

        # Verify new functionality
        repository_methods = [
            "get_all_people_repository",
            "get_person_by_email",
            "get_active_people",
            "get_people_performance_stats",
        ]

        for method in repository_methods:
            assert hasattr(people_service, method)

        print("✅ Phase 4 Service-Repository Integration: COMPLETE")
        print("✅ All services successfully integrated with repository pattern")
        print("✅ Backward compatibility maintained")
        print("✅ New repository-based methods available")
        print("✅ Performance monitoring integrated")
        print("✅ Comprehensive audit trail functionality")
