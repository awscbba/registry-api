"""
Tests for Phase 3 Project Administration Service.

Validates advanced project management capabilities including:
- Advanced search and filtering
- Bulk operations (create, update, delete)
- Project analytics and reporting
- Template management
- Dashboard data generation
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.project_administration_service import (
    ProjectAdministrationService,
    ProjectSortField,
    SortOrder,
    BulkOperationResult,
    ProjectTemplate,
)
from src.models.project import ProjectCreate, ProjectStatus


class TestProjectAdministrationService:
    """Test the ProjectAdministrationService class."""

    def setup_method(self):
        """Set up test environment."""
        self.service = ProjectAdministrationService()

        # Mock the repository to avoid database dependencies
        self.service.project_repository = AsyncMock()

        # Setup default mock responses
        self.service.project_repository.count.return_value = AsyncMock(
            success=True, data=10
        )
        self.service.project_repository.get_all.return_value = AsyncMock(
            success=True, data=self._create_sample_projects()
        )

    def _create_sample_projects(self):
        """Create sample project data for testing."""
        base_date = datetime.utcnow()

        return [
            {
                "id": "proj-1",
                "name": "Software Development Project",
                "description": "Building a web application",
                "startDate": "2024-01-15",
                "endDate": "2024-06-15",
                "maxParticipants": 10,
                "status": "active",
                "category": "Software Development",
                "location": "Remote",
                "requirements": "Programming experience",
                "createdAt": (base_date - timedelta(days=30)).isoformat(),
                "updatedAt": (base_date - timedelta(days=5)).isoformat(),
                "createdBy": "admin",
            },
            {
                "id": "proj-2",
                "name": "Research Project",
                "description": "AI research initiative",
                "startDate": "2024-02-01",
                "endDate": "2024-08-01",
                "maxParticipants": 5,
                "status": "pending",
                "category": "Research",
                "location": "University Lab",
                "requirements": "PhD in AI",
                "createdAt": (base_date - timedelta(days=20)).isoformat(),
                "updatedAt": (base_date - timedelta(days=2)).isoformat(),
                "createdBy": "researcher",
            },
            {
                "id": "proj-3",
                "name": "Community Event",
                "description": "Annual tech conference",
                "startDate": "2024-03-15",
                "endDate": "2024-03-17",
                "maxParticipants": 200,
                "status": "completed",
                "category": "Community",
                "location": "Convention Center",
                "requirements": "Open to all",
                "createdAt": (base_date - timedelta(days=60)).isoformat(),
                "updatedAt": (base_date - timedelta(days=10)).isoformat(),
                "createdBy": "organizer",
            },
        ]

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that the service initializes correctly."""
        result = await self.service.initialize()

        assert result is True
        assert self.service.service_name == "project_administration"
        assert len(self.service.templates) == 3  # Default templates
        self.service.project_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self):
        """Test service initialization with repository failure."""
        self.service.project_repository.count.return_value = AsyncMock(
            success=False, error="Connection failed"
        )

        result = await self.service.initialize()

        assert result is False

    def test_default_templates_creation(self):
        """Test that default templates are created correctly."""
        templates = list(self.service.templates.values())

        assert len(templates) == 3

        template_names = [t["name"] for t in templates]
        assert "Software Development Project" in template_names
        assert "Research Project" in template_names
        assert "Community Event" in template_names

        # Check template structure
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "template_data" in template
            assert "created_at" in template
            assert "usage_count" in template
            assert template["usage_count"] == 0

    @pytest.mark.asyncio
    async def test_search_projects_basic(self):
        """Test basic project search functionality."""
        result = await self.service.search_projects()

        assert result["success"] is True
        assert result["total_count"] == 3
        assert result["filtered_count"] == 3
        assert len(result["projects"]) == 3
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_search_projects_with_query(self):
        """Test project search with text query."""
        result = await self.service.search_projects(query="software")

        assert result["success"] is True
        assert result["filtered_count"] == 1
        assert len(result["projects"]) == 1
        assert result["projects"][0]["name"] == "Software Development Project"

    @pytest.mark.asyncio
    async def test_search_projects_with_status_filter(self):
        """Test project search with status filter."""
        result = await self.service.search_projects(status=ProjectStatus.ACTIVE)

        assert result["success"] is True
        assert result["filtered_count"] == 1
        assert len(result["projects"]) == 1
        assert result["projects"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_search_projects_with_category_filter(self):
        """Test project search with category filter."""
        result = await self.service.search_projects(category="Research")

        assert result["success"] is True
        assert result["filtered_count"] == 1
        assert len(result["projects"]) == 1
        assert result["projects"][0]["category"] == "Research"

    @pytest.mark.asyncio
    async def test_search_projects_with_participant_range(self):
        """Test project search with participant count filters."""
        result = await self.service.search_projects(min_participants=50)

        assert result["success"] is True
        assert result["filtered_count"] == 1
        assert len(result["projects"]) == 1
        assert result["projects"][0]["maxParticipants"] == 200

    @pytest.mark.asyncio
    async def test_search_projects_with_sorting(self):
        """Test project search with custom sorting."""
        result = await self.service.search_projects(
            sort_by=ProjectSortField.NAME, sort_order=SortOrder.ASC
        )

        assert result["success"] is True
        assert len(result["projects"]) == 3

        # Check if sorted by name ascending
        project_names = [p["name"] for p in result["projects"]]
        assert project_names == sorted(project_names)

    @pytest.mark.asyncio
    async def test_search_projects_with_pagination(self):
        """Test project search with pagination."""
        result = await self.service.search_projects(limit=2, offset=0)

        assert result["success"] is True
        assert result["returned_count"] == 2
        assert result["has_more"] is True
        assert result["offset"] == 0
        assert result["limit"] == 2

    @pytest.mark.asyncio
    async def test_search_projects_repository_failure(self):
        """Test project search with repository failure."""
        self.service.project_repository.get_all.return_value = AsyncMock(
            success=False, error="Database connection failed"
        )

        result = await self.service.search_projects()

        assert result["success"] is False
        assert "Database connection failed" in result["error"]
        assert result["projects"] == []

    @pytest.mark.asyncio
    async def test_bulk_create_projects_success(self):
        """Test successful bulk project creation."""
        # Mock successful creation
        self.service.project_repository.create.return_value = AsyncMock(
            success=True, data={}
        )

        projects_data = [
            ProjectCreate(
                name="Test Project 1",
                description="Test description 1",
                startDate="2024-01-01",
                endDate="2024-06-01",
                maxParticipants=10,
            ),
            ProjectCreate(
                name="Test Project 2",
                description="Test description 2",
                startDate="2024-02-01",
                endDate="2024-07-01",
                maxParticipants=15,
            ),
        ]

        result = await self.service.bulk_create_projects(projects_data)

        assert result.total_processed == 2
        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.to_dict()["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_bulk_create_projects_partial_failure(self):
        """Test bulk project creation with some failures."""
        # Create a simple counter to alternate success/failure
        call_count = 0

        async def mock_create(project_id, project_data):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                mock_result = AsyncMock()
                mock_result.success = False
                mock_result.error = "Creation failed"
                return mock_result
            else:  # First call succeeds
                mock_result = AsyncMock()
                mock_result.success = True
                mock_result.data = {}
                return mock_result

        self.service.project_repository.create.side_effect = mock_create

        projects_data = [
            ProjectCreate(
                name="Success Project",
                description="This will succeed",
                startDate="2024-01-01",
                endDate="2024-06-01",
                maxParticipants=10,
            ),
            ProjectCreate(
                name="Fail Project",
                description="This will fail",
                startDate="2024-02-01",
                endDate="2024-07-01",
                maxParticipants=15,
            ),
        ]

        result = await self.service.bulk_create_projects(projects_data)

        assert result.total_processed == 2
        assert len(result.successful) == 1
        assert len(result.failed) == 1
        assert result.to_dict()["success_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_bulk_update_projects_success(self):
        """Test successful bulk project updates."""
        self.service.project_repository.update.return_value = AsyncMock(
            success=True, data={}
        )

        updates_data = [
            {"id": "proj-1", "status": "completed"},
            {"id": "proj-2", "maxParticipants": 20},
        ]

        result = await self.service.bulk_update_projects(updates_data)

        assert result.total_processed == 2
        assert len(result.successful) == 2
        assert len(result.failed) == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_projects_success(self):
        """Test successful bulk project deletion."""
        self.service.project_repository.delete.return_value = AsyncMock(
            success=True, data={}
        )

        project_ids = ["proj-1", "proj-2"]

        result = await self.service.bulk_delete_projects(project_ids)

        assert result.total_processed == 2
        assert len(result.successful) == 2
        assert len(result.failed) == 0

    @pytest.mark.asyncio
    async def test_get_project_analytics_success(self):
        """Test project analytics generation."""
        analytics = await self.service.get_project_analytics(days=30)

        assert analytics["success"] is True
        assert "overview" in analytics
        assert "status_distribution" in analytics
        assert "category_distribution" in analytics
        assert "monthly_trends" in analytics

        # Check overview statistics
        overview = analytics["overview"]
        assert overview["total_projects"] == 3
        assert "recent_projects" in overview
        assert "upcoming_projects" in overview

        # Check status distribution
        status_dist = analytics["status_distribution"]
        assert status_dist["active"] == 1
        assert status_dist["pending"] == 1
        assert status_dist["completed"] == 1

        # Check category distribution
        category_dist = analytics["category_distribution"]
        assert "Software Development" in category_dist
        assert "Research" in category_dist
        assert "Community" in category_dist

    @pytest.mark.asyncio
    async def test_get_project_analytics_repository_failure(self):
        """Test project analytics with repository failure."""
        self.service.project_repository.get_all.return_value = AsyncMock(
            success=False, error="Database error"
        )

        analytics = await self.service.get_project_analytics()

        assert analytics["success"] is False
        assert "Database error" in analytics["error"]

    @pytest.mark.asyncio
    async def test_get_project_templates(self):
        """Test getting project templates."""
        result = await self.service.get_project_templates()

        assert result["success"] is True
        assert result["total_count"] == 3
        assert len(result["templates"]) == 3

        # Check template structure
        template = result["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "template_data" in template
        assert "usage_count" in template

    @pytest.mark.asyncio
    async def test_create_project_from_template_success(self):
        """Test creating project from template."""
        self.service.project_repository.create.return_value = AsyncMock(
            success=True, data={"id": "new-proj-id"}
        )

        # Get a template ID
        template_id = list(self.service.templates.keys())[0]
        project_data = {
            "name": "Custom Project Name",
            "description": "Custom description",
            "startDate": "2024-01-01",
            "endDate": "2024-06-01",
        }

        result = await self.service.create_project_from_template(
            template_id, project_data
        )

        assert result["success"] is True
        assert result["template_used"] == template_id
        assert "project_id" in result

        # Check that template usage count was incremented
        template = self.service.templates[template_id]
        assert template["usage_count"] == 1

    @pytest.mark.asyncio
    async def test_create_project_from_template_not_found(self):
        """Test creating project from non-existent template."""
        result = await self.service.create_project_from_template(
            "invalid-template-id", {}
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self):
        """Test dashboard data generation."""
        dashboard_data = await self.service.get_dashboard_data()

        assert dashboard_data["success"] is True
        assert "dashboard_data" in dashboard_data

        dashboard = dashboard_data["dashboard_data"]
        assert "overview" in dashboard
        assert "analytics" in dashboard
        assert "recent_projects" in dashboard
        assert "projects_by_status" in dashboard
        assert "templates" in dashboard
        assert "quick_stats" in dashboard

        # Check quick stats
        quick_stats = dashboard["quick_stats"]
        assert "total_projects" in quick_stats
        assert "active_projects" in quick_stats
        assert "pending_projects" in quick_stats
        assert "completed_projects" in quick_stats

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test service health check."""
        health = await self.service.health_check()

        assert health["healthy"] is True
        assert health["status"] == "operational"
        assert health["repository_accessible"] is True
        assert health["templates_loaded"] == 3
        assert "last_check" in health
        assert health["error"] is None

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test service health check with repository failure."""
        self.service.project_repository.count.return_value = AsyncMock(
            success=False, error="Connection timeout"
        )

        health = await self.service.health_check()

        assert health["healthy"] is False
        assert health["status"] == "error"
        assert health["repository_accessible"] is False
        assert "Connection timeout" in health["error"]


class TestBulkOperationResult:
    """Test the BulkOperationResult class."""

    def test_bulk_operation_result_initialization(self):
        """Test BulkOperationResult initialization."""
        result = BulkOperationResult()

        assert result.successful == []
        assert result.failed == []
        assert result.total_processed == 0

    def test_add_success(self):
        """Test adding successful operations."""
        result = BulkOperationResult()

        result.add_success("item-1")
        result.add_success("item-2")

        assert len(result.successful) == 2
        assert "item-1" in result.successful
        assert "item-2" in result.successful
        assert result.total_processed == 2

    def test_add_failure(self):
        """Test adding failed operations."""
        result = BulkOperationResult()

        result.add_failure("item-1", "Error message 1")
        result.add_failure("item-2", "Error message 2")

        assert len(result.failed) == 2
        assert result.failed[0]["id"] == "item-1"
        assert result.failed[0]["error"] == "Error message 1"
        assert result.total_processed == 2

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = BulkOperationResult()

        result.add_success("success-1")
        result.add_success("success-2")
        result.add_failure("fail-1", "Error")

        result_dict = result.to_dict()

        assert result_dict["total_processed"] == 3
        assert result_dict["successful_count"] == 2
        assert result_dict["failed_count"] == 1
        assert result_dict["success_rate"] == 66.66666666666666
        assert len(result_dict["successful_ids"]) == 2
        assert len(result_dict["failures"]) == 1


class TestProjectTemplate:
    """Test the ProjectTemplate class."""

    def test_project_template_creation(self):
        """Test ProjectTemplate creation."""
        template_data = {"category": "Test Category", "maxParticipants": 10}

        template = ProjectTemplate(
            name="Test Template",
            description="Test description",
            template_data=template_data,
        )

        assert template["name"] == "Test Template"
        assert template["description"] == "Test description"
        assert template["template_data"] == template_data
        assert template["usage_count"] == 0
        assert "id" in template
        assert "created_at" in template

    def test_project_template_inheritance(self):
        """Test that ProjectTemplate inherits from dict."""
        template = ProjectTemplate("Test", "Description", {})

        # Should behave like a dictionary
        assert isinstance(template, dict)
        assert template["name"] == "Test"

        # Should support dict operations
        template["custom_field"] = "custom_value"
        assert template["custom_field"] == "custom_value"


class TestProjectAdministrationServiceFiltering:
    """Test the filtering logic in ProjectAdministrationService."""

    def setup_method(self):
        """Set up test environment."""
        self.service = ProjectAdministrationService()

        # Create test projects with various attributes
        self.test_projects = [
            {
                "id": "1",
                "name": "Web Development Project",
                "description": "Building a modern web application",
                "startDate": "2024-01-15",
                "endDate": "2024-06-15",
                "maxParticipants": 10,
                "status": "active",
                "category": "Software Development",
                "location": "Remote",
            },
            {
                "id": "2",
                "name": "Mobile App Research",
                "description": "Research on mobile app development",
                "startDate": "2024-02-01",
                "endDate": "2024-08-01",
                "maxParticipants": 5,
                "status": "pending",
                "category": "Research",
                "location": "University",
            },
            {
                "id": "3",
                "name": "Community Workshop",
                "description": "Workshop for community members",
                "startDate": "2024-03-15",
                "endDate": "2024-03-17",
                "maxParticipants": 50,
                "status": "completed",
                "category": "Community",
                "location": "Community Center",
            },
        ]

    def test_apply_filters_query(self):
        """Test text query filtering."""
        filtered = self.service._apply_filters(
            self.test_projects,
            query="web",
            status=None,
            category=None,
            start_date_from=None,
            start_date_to=None,
            end_date_from=None,
            end_date_to=None,
            min_participants=None,
            max_participants=None,
            location=None,
        )

        assert len(filtered) == 1
        assert filtered[0]["name"] == "Web Development Project"

    def test_apply_filters_status(self):
        """Test status filtering."""
        filtered = self.service._apply_filters(
            self.test_projects,
            query=None,
            status=ProjectStatus.ACTIVE,
            category=None,
            start_date_from=None,
            start_date_to=None,
            end_date_from=None,
            end_date_to=None,
            min_participants=None,
            max_participants=None,
            location=None,
        )

        assert len(filtered) == 1
        assert filtered[0]["status"] == "active"

    def test_apply_filters_participants_range(self):
        """Test participant count range filtering."""
        filtered = self.service._apply_filters(
            self.test_projects,
            query=None,
            status=None,
            category=None,
            start_date_from=None,
            start_date_to=None,
            end_date_from=None,
            end_date_to=None,
            min_participants=20,
            max_participants=100,
            location=None,
        )

        assert len(filtered) == 1
        assert filtered[0]["maxParticipants"] == 50

    def test_apply_filters_location(self):
        """Test location filtering."""
        filtered = self.service._apply_filters(
            self.test_projects,
            query=None,
            status=None,
            category=None,
            start_date_from=None,
            start_date_to=None,
            end_date_from=None,
            end_date_to=None,
            min_participants=None,
            max_participants=None,
            location="remote",
        )

        assert len(filtered) == 1
        assert "Remote" in filtered[0]["location"]

    def test_sort_projects_by_name(self):
        """Test sorting projects by name."""
        sorted_projects = self.service._sort_projects(
            self.test_projects, ProjectSortField.NAME, SortOrder.ASC
        )

        names = [p["name"] for p in sorted_projects]
        assert names == sorted(names)

    def test_sort_projects_by_participants_desc(self):
        """Test sorting projects by participants descending."""
        sorted_projects = self.service._sort_projects(
            self.test_projects, ProjectSortField.MAX_PARTICIPANTS, SortOrder.DESC
        )

        participants = [p["maxParticipants"] for p in sorted_projects]
        assert participants == sorted(participants, reverse=True)
