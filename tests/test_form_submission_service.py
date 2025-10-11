"""
Form Submission Service Tests for Dynamic Form Builder
Test-Driven Development approach - these tests will FAIL initially
"""

import pytest
from unittest.mock import Mock, patch
from src.services.form_submission_service import FormSubmissionService
from src.models.dynamic_forms import (
    ProjectSubmissionCreate,
    ProjectSubmission,
    CustomField,
    FormSchema,
)


class TestFormSubmissionService:
    """Test form submission service with dynamic forms support"""

    def setup_method(self):
        """Setup test fixtures"""
        # Mock the repository following dependency injection pattern
        self.mock_repository = Mock()
        self.submission_service = FormSubmissionService(self.mock_repository)

    def test_submit_dynamic_form_responses(self):
        """Test submitting form responses with validation"""
        # Arrange
        submission_data = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={
                "experience": "Intermediate",
                "skills": ["Python", "AWS"],
                "availability": "Full-time",
            },
        )

        self.mock_repository.create.return_value = {
            "id": "submission-789",
            "projectId": "project-123",
            "personId": "person-456",
            "responses": submission_data.responses,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
        }

        # Act
        result = self.submission_service.submit_form_responses(submission_data)

        # Assert
        assert result is not None
        assert result.projectId == "project-123"
        assert result.personId == "person-456"
        self.mock_repository.create.assert_called_once()

    def test_validate_required_fields(self):
        """Test validation of required fields"""
        # Arrange - Form schema with required fields
        required_field = CustomField(
            id="experience",
            type="poll_single",
            question="Experience level?",
            options=["Beginner", "Intermediate", "Advanced"],
            required=True,
        )

        form_schema = FormSchema(
            version="1.0", fields=[required_field], richTextDescription="Test form"
        )

        # Missing required field
        incomplete_submission = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={"skills": ["Python"]},  # Missing required 'experience'
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Required field 'experience' is missing"):
            self.submission_service.validate_submission_against_schema(
                incomplete_submission, form_schema
            )

    def test_validate_poll_responses(self):
        """Test validation of poll response values"""
        # Arrange - Single choice poll
        single_choice_field = CustomField(
            id="experience",
            type="poll_single",
            question="Experience level?",
            options=["Beginner", "Intermediate", "Advanced"],
            required=True,
        )

        form_schema = FormSchema(
            version="1.0", fields=[single_choice_field], richTextDescription="Test form"
        )

        # Invalid response (not in options)
        invalid_submission = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={"experience": "Expert"},  # Not in allowed options
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Invalid option 'Expert' for field 'experience'"
        ):
            self.submission_service.validate_submission_against_schema(
                invalid_submission, form_schema
            )

    def test_get_project_submissions(self):
        """Test retrieving all submissions for a project"""
        # Arrange
        project_id = "project-123"
        mock_submissions = [
            {
                "id": "sub-1",
                "projectId": project_id,
                "personId": "person-1",
                "responses": {"experience": "Beginner"},
                "createdAt": "2025-01-01T00:00:00",
                "updatedAt": "2025-01-01T00:00:00",
            },
            {
                "id": "sub-2",
                "projectId": project_id,
                "personId": "person-2",
                "responses": {"experience": "Advanced"},
                "createdAt": "2025-01-01T01:00:00",
                "updatedAt": "2025-01-01T01:00:00",
            },
        ]

        self.mock_repository.get_by_project_id.return_value = mock_submissions

        # Act
        result = self.submission_service.get_project_submissions(project_id)

        # Assert
        assert len(result) == 2
        assert all(sub.projectId == project_id for sub in result)
        self.mock_repository.get_by_project_id.assert_called_once_with(project_id)

    def test_submission_data_integrity(self):
        """Test that submission data maintains integrity"""
        # Arrange
        submission_data = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={
                "text_field": "Some text response",
                "number_field": 42,
                "array_field": ["option1", "option2"],
                "nested_field": {"key": "value"},
            },
        )

        self.mock_repository.create.return_value = {
            "id": "submission-789",
            "projectId": submission_data.projectId,
            "personId": submission_data.personId,
            "responses": submission_data.responses,
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
        }

        # Act
        result = self.submission_service.submit_form_responses(submission_data)

        # Assert - Data integrity maintained
        assert result.responses["text_field"] == "Some text response"
        assert result.responses["number_field"] == 42
        assert result.responses["array_field"] == ["option1", "option2"]
        assert result.responses["nested_field"]["key"] == "value"

    def test_multiple_choice_poll_validation(self):
        """Test validation of multiple choice poll responses"""
        # Arrange - Multiple choice poll
        multi_choice_field = CustomField(
            id="skills",
            type="poll_multiple",
            question="Which skills do you have?",
            options=["Python", "JavaScript", "AWS", "Docker"],
            required=True,
        )

        form_schema = FormSchema(
            version="1.0",
            fields=[multi_choice_field],
            richTextDescription="Skills form",
        )

        # Valid multiple selection
        valid_submission = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={"skills": ["Python", "AWS"]},
        )

        # Act & Assert - Should not raise exception
        result = self.submission_service.validate_submission_against_schema(
            valid_submission, form_schema
        )
        assert result is True

        # Invalid multiple selection (contains invalid option)
        invalid_submission = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={"skills": ["Python", "InvalidSkill"]},
        )

        # Act & Assert - Should raise exception
        with pytest.raises(
            ValueError, match="Invalid option 'InvalidSkill' for field 'skills'"
        ):
            self.submission_service.validate_submission_against_schema(
                invalid_submission, form_schema
            )

    def test_get_submission_by_person_and_project(self):
        """Test retrieving specific submission by person and project"""
        # Arrange
        project_id = "project-123"
        person_id = "person-456"

        mock_submission = {
            "id": "submission-789",
            "projectId": project_id,
            "personId": person_id,
            "responses": {"experience": "Intermediate"},
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
        }

        self.mock_repository.get_by_person_and_project.return_value = mock_submission

        # Act
        result = self.submission_service.get_submission_by_person_and_project(
            person_id, project_id
        )

        # Assert
        assert result is not None
        assert result.projectId == project_id
        assert result.personId == person_id
        self.mock_repository.get_by_person_and_project.assert_called_once_with(
            person_id, project_id
        )
