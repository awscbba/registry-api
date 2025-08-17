"""
Test suite for ProjectRepository field mapping consistency.

This test ensures that ProjectRepository correctly handles camelCase field names
to match the storage pattern used by DefensiveDynamoDBService.

CRITICAL: This test prevents data loss and system inconsistencies.
"""

import pytest
from datetime import datetime
from src.repositories.project_repository import ProjectRepository
from src.models.project import Project, ProjectStatus


class TestProjectRepositoryFieldMapping:
    """Test ProjectRepository field mapping consistency with DefensiveDynamoDBService."""

    def test_project_repository_camelcase_field_consistency(self):
        """Test that ProjectRepository handles camelCase fields correctly."""
        # DynamoDB data as stored by DefensiveDynamoDBService (camelCase)
        dynamodb_item = {
            "id": "test-project-id",
            "name": "Test Project",
            "description": "Test Description for field mapping",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 100,
            "status": "active",
            "category": "Technology",
            "location": "Cochabamba",
            "requirements": "Python experience required",
            "createdBy": "user-123",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T12:00:00Z",
        }

        # Test repository conversion from DynamoDB to Project entity
        repo = ProjectRepository()
        project = repo._to_entity(dynamodb_item)

        # Verify all fields are correctly mapped
        assert project.id == "test-project-id"
        assert project.name == "Test Project"
        assert project.description == "Test Description for field mapping"
        assert project.startDate == "2025-01-01"
        assert project.endDate == "2025-12-31"
        assert project.maxParticipants == 100
        assert project.status == "active"
        assert project.category == "Technology"
        assert project.location == "Cochabamba"
        assert project.requirements == "Python experience required"
        assert project.createdBy == "user-123"
        # DateTime fields are converted to datetime objects
        assert isinstance(project.createdAt, datetime)
        assert isinstance(project.updatedAt, datetime)
        assert project.createdAt.year == 2025
        assert project.createdAt.month == 1
        assert project.createdAt.day == 1

    def test_project_repository_to_item_camelcase_consistency(self):
        """Test that ProjectRepository converts Project entity to camelCase DynamoDB item."""
        # Create Project entity with camelCase fields
        project = Project(
            id="test-project-id",
            name="Test Project",
            description="Test Description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=50,
            status=ProjectStatus.ACTIVE,
            category="Education",
            location="La Paz",
            requirements="Basic programming knowledge",
            createdBy="user-456",
            createdAt=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
            updatedAt=datetime.fromisoformat("2025-01-01T12:00:00+00:00"),
        )

        # Test repository conversion from Project entity to DynamoDB item
        repo = ProjectRepository()
        item = repo._to_item(project)

        # Verify all fields use camelCase (matching DefensiveDynamoDBService)
        assert item["id"] == "test-project-id"
        assert item["name"] == "Test Project"
        assert item["description"] == "Test Description"
        assert item["startDate"] == "2025-01-01"
        assert item["endDate"] == "2025-12-31"
        assert item["maxParticipants"] == 50
        assert item["status"] == "active"
        assert item["category"] == "Education"
        assert item["location"] == "La Paz"
        assert item["requirements"] == "Basic programming knowledge"
        assert item["createdBy"] == "user-456"
        # DateTime fields are converted to ISO strings
        assert isinstance(item["createdAt"], str)
        assert isinstance(item["updatedAt"], str)
        assert "2025-01-01" in item["createdAt"]
        assert "2025-01-01" in item["updatedAt"]

    def test_project_repository_critical_fields_not_missing(self):
        """Test that critical fields like maxParticipants are not missing."""
        # DynamoDB data with all critical fields
        dynamodb_item = {
            "id": "critical-test-id",
            "name": "Critical Test Project",
            "description": "Testing critical field handling",
            "startDate": "2025-06-01",
            "endDate": "2025-08-31",
            "maxParticipants": 200,  # CRITICAL: This field was missing before fix
            "status": "pending",
            "createdBy": "admin-user",
            "createdAt": "2025-01-15T10:30:00Z",
            "updatedAt": "2025-01-15T14:45:00Z",
        }

        repo = ProjectRepository()
        project = repo._to_entity(dynamodb_item)

        # Verify critical field is preserved
        assert project.maxParticipants == 200, "maxParticipants field must not be lost!"

        # Test round-trip conversion
        item_back = repo._to_item(project)
        assert (
            item_back["maxParticipants"] == 200
        ), "maxParticipants must survive round-trip!"

    def test_project_repository_handles_optional_fields(self):
        """Test that optional fields are handled correctly."""
        # Minimal DynamoDB data (only required fields)
        minimal_item = {
            "id": "minimal-project",
            "name": "Minimal Project",
            "description": "Minimal description",
            "startDate": "2025-03-01",
            "endDate": "2025-05-31",
            "maxParticipants": 25,
            "status": "active",
            "createdBy": "user-789",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }

        repo = ProjectRepository()
        project = repo._to_entity(minimal_item)

        # Verify required fields are present
        assert project.id == "minimal-project"
        assert project.maxParticipants == 25
        assert project.createdBy == "user-789"

        # Verify optional fields handle None gracefully
        assert project.category is None or project.category == ""
        assert project.location is None or project.location == ""
        assert project.requirements is None or project.requirements == ""

    def test_project_repository_defensive_dynamodb_service_compatibility(self):
        """Test compatibility with DefensiveDynamoDBService data format."""
        # This is the exact format that DefensiveDynamoDBService creates
        defensive_service_item = {
            "id": "defensive-test-id",
            "name": "Defensive Service Project",
            "description": "Created by DefensiveDynamoDBService",
            "startDate": "2025-02-01",
            "endDate": "2025-11-30",
            "maxParticipants": 150,
            "status": "active",
            "category": "Research",
            "location": "Santa Cruz",
            "requirements": "Advanced degree preferred",
            "createdBy": "service-user",
            "createdAt": "2025-01-20T08:15:30Z",
            "updatedAt": "2025-01-20T16:45:22Z",
        }

        repo = ProjectRepository()
        project = repo._to_entity(defensive_service_item)

        # Verify ProjectRepository can read DefensiveDynamoDBService data
        assert project.id == "defensive-test-id"
        assert project.name == "Defensive Service Project"
        assert project.startDate == "2025-02-01"
        assert project.endDate == "2025-11-30"
        assert project.maxParticipants == 150
        assert project.createdBy == "service-user"
        # DateTime fields are converted to datetime objects
        assert isinstance(project.createdAt, datetime)
        assert isinstance(project.updatedAt, datetime)

        # Test that ProjectRepository can write data that DefensiveDynamoDBService can read
        item_back = repo._to_item(project)

        # Verify all fields use camelCase (DefensiveDynamoDBService format)
        expected_camelcase_fields = [
            "startDate",
            "endDate",
            "maxParticipants",
            "createdBy",
            "createdAt",
            "updatedAt",
        ]

        for field in expected_camelcase_fields:
            assert field in item_back, f"Field {field} must be in camelCase format"
            assert (
                f"{field.lower()}_" not in item_back
            ), f"Field {field} must not be in snake_case"

    def test_project_repository_no_data_loss(self):
        """Test that no data is lost during field mapping conversions."""
        # Complete project data with all possible fields
        complete_item = {
            "id": "complete-project-id",
            "name": "Complete Test Project",
            "description": "Project with all fields populated",
            "startDate": "2025-04-01",
            "endDate": "2025-09-30",
            "maxParticipants": 300,
            "status": "ongoing",
            "category": "Community",
            "location": "Tarija",
            "requirements": "Community involvement required",
            "createdBy": "community-admin",
            "createdAt": "2025-01-10T09:00:00Z",
            "updatedAt": "2025-01-25T15:30:00Z",
        }

        repo = ProjectRepository()

        # Convert to entity and back to item
        project = repo._to_entity(complete_item)
        item_back = repo._to_item(project)

        # Verify no data loss in critical fields (excluding datetime format differences)
        critical_fields = [
            "id",
            "name",
            "description",
            "startDate",
            "endDate",
            "maxParticipants",
            "status",
            "createdBy",
        ]

        for field in critical_fields:
            original_value = complete_item[field]
            converted_value = item_back[field]
            assert (
                converted_value == original_value
            ), f"Data loss in field {field}: {original_value} != {converted_value}"

        # Verify datetime fields are preserved (allowing for format differences)
        assert "2025-01-10" in item_back["createdAt"]
        assert "2025-01-25" in item_back["updatedAt"]

    def test_project_repository_field_name_consistency(self):
        """Test that field names are consistent with system standards."""
        # Test data
        test_item = {
            "id": "consistency-test",
            "name": "Consistency Test",
            "description": "Testing field name consistency",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 100,
            "createdBy": "test-user",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }

        repo = ProjectRepository()
        project = repo._to_entity(test_item)
        item_back = repo._to_item(project)

        # Verify no snake_case fields in output (should all be camelCase)
        snake_case_fields = [
            "start_date",
            "end_date",
            "max_participants",
            "created_by",
            "created_at",
            "updated_at",
        ]

        for field in snake_case_fields:
            assert (
                field not in item_back
            ), f"Snake_case field {field} should not exist in output"

        # Verify camelCase fields are present
        camelcase_fields = [
            "startDate",
            "endDate",
            "maxParticipants",
            "createdBy",
            "createdAt",
            "updatedAt",
        ]

        for field in camelcase_fields:
            assert (
                field in item_back
            ), f"CamelCase field {field} must be present in output"

    def test_project_repository_datetime_handling(self):
        """Test that datetime fields are handled correctly in both directions."""
        # Test with ISO string input
        item_with_string_dates = {
            "id": "datetime-test",
            "name": "DateTime Test",
            "description": "Testing datetime conversion",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 50,
            "createdBy": "datetime-user",
            "createdAt": "2025-01-01T10:30:45Z",
            "updatedAt": "2025-01-01T14:15:30Z",
        }

        repo = ProjectRepository()

        # Convert string dates to Project entity (should become datetime objects)
        project = repo._to_entity(item_with_string_dates)
        assert isinstance(project.createdAt, datetime)
        assert isinstance(project.updatedAt, datetime)

        # Convert back to item (should become ISO strings)
        item_back = repo._to_item(project)
        assert isinstance(item_back["createdAt"], str)
        assert isinstance(item_back["updatedAt"], str)
        assert "2025-01-01" in item_back["createdAt"]
        assert "2025-01-01" in item_back["updatedAt"]
