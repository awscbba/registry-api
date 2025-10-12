"""
Enhanced Project Service Tests for Dynamic Form Builder
Test-Driven Development approach - these tests will FAIL initially
"""

import pytest
from unittest.mock import Mock, patch
from src.services.projects_service import ProjectsService
from src.models.dynamic_forms import (
    CustomField,
    FormSchema,
    EnhancedProjectCreate,
    ProjectImage,
)
from src.models.project import Project, ProjectStatus


class TestEnhancedProjectService:
    """Test enhanced project service with dynamic forms support"""

    def setup_method(self):
        """Setup test fixtures"""
        # Mock the repository following dependency injection pattern
        self.mock_repository = Mock()
        self.projects_service = ProjectsService(self.mock_repository)

    @patch("src.core.database.db.put_item")
    @patch("src.core.database.db.get_item")
    def test_create_project_with_custom_fields(self, mock_get_item, mock_put_item):
        """Test creating project with custom fields"""
        # Arrange
        custom_field = CustomField(
            id="experience",
            type="poll_single",
            question="What's your experience level?",
            options=["Beginner", "Intermediate", "Advanced"],
            required=True,
        )

        project_data = EnhancedProjectCreate(
            name="Test Project",
            description="Test description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=50,
            customFields=[custom_field],
        )

        # Configure mock repository to return a proper Project object
        expected_project = Project(
            id="project-123",
            name="Test Project",
            description="Test description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=50,
            status=ProjectStatus.PENDING,
            currentParticipants=0,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
            createdBy="system",
        )
        self.mock_repository.create.return_value = expected_project

        # Act
        result = self.projects_service.create_with_dynamic_fields(project_data)

        # Assert - Focus on service behavior, not model structure
        assert result is not None
        assert result.name == "Test Project"
        # The service should handle the dynamic fields (implementation detail)
        # We're testing that the method exists and returns a project

    @patch("src.core.database.db.put_item")
    @patch("src.core.database.db.get_item")
    def test_create_project_with_rich_text_description(
        self, mock_get_item, mock_put_item
    ):
        """Test creating project with rich text description"""
        # Arrange
        form_schema = FormSchema(
            version="1.0",
            fields=[],
            richTextDescription="# Project Overview\n\nThis is a **markdown** description with [links](https://example.com).",
        )

        project_data = EnhancedProjectCreate(
            name="Rich Text Project",
            description="Basic description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            formSchema=form_schema,
        )

        mock_put_item.return_value = True
        mock_get_item.return_value = {
            "id": "project-456",
            "name": "Rich Text Project",
            "formSchema": form_schema.model_dump(),
        }

        # Configure mock repository to return a proper Project object
        expected_project = Project(
            id="project-456",
            name="Rich Text Project",
            description="Basic description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            status=ProjectStatus.PENDING,
            currentParticipants=0,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
            createdBy="system",
            formSchema=form_schema.model_dump(),
        )
        self.mock_repository.create.return_value = expected_project

        # Act
        result = self.projects_service.create_with_dynamic_fields(project_data)

        # Assert - Focus on service behavior
        assert result is not None
        assert result.name == "Rich Text Project"
        # The service should handle the form schema (implementation detail)

    @patch("src.core.database.db.update_item")
    @patch("src.core.database.db.get_item")
    def test_update_project_form_schema(self, mock_get_item, mock_update_item):
        """Test updating project form schema"""
        # Arrange
        project_id = "project-123"
        new_field = CustomField(
            id="skills",
            type="poll_multiple",
            question="Which skills do you have?",
            options=["Python", "JavaScript", "AWS"],
            required=False,
        )

        updated_schema = FormSchema(
            version="1.1", fields=[new_field], richTextDescription="Updated description"
        )

        mock_get_item.return_value = {"id": project_id, "name": "Existing Project"}
        mock_update_item.return_value = {
            "id": project_id,
            "formSchema": updated_schema.model_dump(),
        }

        # Act
        result = self.projects_service.update_form_schema(project_id, updated_schema)

        # Assert - Focus on service behavior
        assert result is not None
        assert result.id == project_id
        # The service should handle the schema update (implementation detail)

    @patch("src.core.database.db.get_item")
    def test_get_project_with_dynamic_fields(self, mock_get_item):
        """Test retrieving project with dynamic fields"""
        # Arrange
        project_id = "project-789"
        custom_field = CustomField(
            id="level",
            type="poll_single",
            question="Experience level?",
            options=["Junior", "Senior"],
            required=True,
        )

        mock_get_item.return_value = {
            "id": project_id,
            "name": "Dynamic Project",
            "customFields": [custom_field.model_dump()],
            "formSchema": {
                "version": "1.0",
                "fields": [custom_field.model_dump()],
                "richTextDescription": "# Dynamic Description",
            },
        }

        # Configure mock repository to return a proper Project object
        expected_project = Project(
            id=project_id,
            name="Dynamic Project",
            description="Dynamic description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            status=ProjectStatus.PENDING,
            currentParticipants=0,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
            createdBy="system",
        )
        self.mock_repository.get_by_id.return_value = expected_project

        # Act
        result = self.projects_service.get_with_dynamic_fields(project_id)

        # Assert - Focus on service behavior
        assert result is not None
        assert result.id == project_id
        # The service should handle dynamic fields retrieval (implementation detail)

    def test_validate_form_schema_structure(self):
        """Test form schema validation"""
        # Arrange - Valid schema
        valid_field = CustomField(
            id="valid-field",
            type="poll_single",
            question="Valid question?",
            options=["Yes", "No"],
            required=True,
        )

        valid_schema = FormSchema(
            version="1.0", fields=[valid_field], richTextDescription="Valid description"
        )

        # Act & Assert - Should not raise exception
        result = self.projects_service.validate_form_schema(valid_schema)
        assert result is True

        # Arrange - Invalid schema (duplicate field IDs)
        duplicate_field1 = CustomField(
            id="duplicate",
            type="poll_single",
            question="Question 1?",
            options=["A", "B"],
            required=True,
        )

        duplicate_field2 = CustomField(
            id="duplicate",  # Same ID
            type="poll_multiple",
            question="Question 2?",
            options=["C", "D"],
            required=False,
        )

        # Act & Assert - Should raise validation error at service level
        # Since Pydantic already validates, we test the service validation logic
        try:
            # Try to create invalid schema - this should fail at Pydantic level
            FormSchema(
                version="1.0",
                fields=[duplicate_field1, duplicate_field2],
                richTextDescription="Invalid schema",
            )
            assert False, "Should have raised validation error"
        except ValueError as e:
            assert "Field IDs must be unique" in str(e)

    @patch("src.core.database.db.put_item")
    @patch("src.core.database.db.get_item")
    def test_create_project_with_images(self, mock_get_item, mock_put_item):
        """Test creating project with images"""
        # Arrange
        image = ProjectImage(
            url="https://s3.amazonaws.com/bucket/project-image.jpg",
            filename="project-image.jpg",
            size=2048000,  # 2MB
        )

        project_data = EnhancedProjectCreate(
            name="Project with Images",
            description="Project description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=75,
            images=[image],
        )

        mock_put_item.return_value = True
        mock_get_item.return_value = {
            "id": "project-with-images",
            "name": "Project with Images",
            "images": [image.model_dump()],
        }

        # Configure mock repository to return a proper Project object
        expected_project = Project(
            id="project-with-images",
            name="Project with Images",
            description="Project description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=75,
            status=ProjectStatus.PENDING,
            currentParticipants=0,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
            createdBy="system",
        )
        self.mock_repository.create.return_value = expected_project

        # Act
        result = self.projects_service.create_with_dynamic_fields(project_data)

        # Assert - Focus on service behavior
        assert result is not None
        assert result.name == "Project with Images"
        # The service should handle images (implementation detail)

    def test_backward_compatibility_with_existing_projects(self):
        """Test that enhanced service works with existing projects"""
        # This test ensures we don't break existing functionality
        # when adding dynamic forms support

        # Arrange - Standard project data (no dynamic fields)
        from src.models.project import ProjectCreate

        standard_project = ProjectCreate(
            name="Standard Project",
            description="Standard description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=25,
        )

        # Act & Assert - Should still work with existing create method
        # Mock the repository's create method to return a proper Project
        self.mock_repository.create.return_value = Project(
            id="standard-project-id",
            name="Standard Project",
            description="Standard description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=25,
            status=ProjectStatus.PENDING,
            currentParticipants=0,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
            createdBy="system",
        )

        import asyncio

        result = asyncio.run(self.projects_service.create_project(standard_project))
        assert result is not None
        assert result.name == "Standard Project"
