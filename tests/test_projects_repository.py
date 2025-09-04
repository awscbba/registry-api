"""
Tests for ProjectsRepository to ensure proper configuration and initialization.
"""

import pytest
from unittest.mock import patch
from src.repositories.projects_repository import ProjectsRepository


class TestProjectsRepository:
    """Test ProjectsRepository configuration and initialization."""

    def test_repository_initialization_loads_config(self):
        """Test that repository initialization loads config without errors."""
        # This test would have caught the AttributeError: 'DatabaseConfig' object has no attribute 'projects_table_v2'
        try:
            repo = ProjectsRepository()
            # Should have a table_name attribute
            assert hasattr(repo, "table_name")
            assert repo.table_name is not None
            assert isinstance(repo.table_name, str)
            print(f"✅ Repository initialized with table_name: {repo.table_name}")
        except AttributeError as e:
            pytest.fail(f"Repository initialization failed with config error: {e}")

    def test_repository_table_name_not_hardcoded(self):
        """Test that table name is not hardcoded."""
        repo = ProjectsRepository()

        # Should not be the old hardcoded value
        assert repo.table_name != "projects"

        # Should be a proper table name from config
        assert "Table" in repo.table_name or "table" in repo.table_name

    @patch("src.core.database.db.put_item")
    async def test_create_project_uses_repository_table_name(self, mock_put_item):
        """Test that create method uses the repository's configured table name."""
        mock_put_item.return_value = True

        repo = ProjectsRepository()

        # Mock project data
        from src.models.project import ProjectCreate

        project_data = ProjectCreate(
            name="Test Project",
            description="Test Description",
            startDate="2025-03-01",
            endDate="2025-06-30",
            maxParticipants=10,
            status="pending",
            category="Test",
            location="Test Location",
            requirements="None",
        )

        await repo.create(project_data)

        # Verify put_item was called with the repository's table name
        mock_put_item.assert_called_once()
        call_args = mock_put_item.call_args
        table_name_used = call_args[0][0]

        # Should use the same table name as configured in repository
        assert table_name_used == repo.table_name

        # Should not be the old hardcoded value
        assert table_name_used != "projects"
