"""
Pydantic Models Tests for Dynamic Form Builder
Test-Driven Development approach - comprehensive model validation testing
"""

import pytest
from pydantic import ValidationError
from src.models.dynamic_forms import (
    CustomField,
    ProjectImage,
    FormSchema,
    ProjectSubmissionBase,
    ProjectSubmissionCreate,
    ProjectSubmission,
    EnhancedProjectBase,
    EnhancedProjectCreate,
    EnhancedProject,
)
from datetime import datetime


class TestCustomFieldModel:
    """Test CustomField model validation and business rules"""

    def test_valid_custom_field_creation(self):
        """Test creating valid custom fields"""
        # Test poll_single
        field = CustomField(
            id="field-1",
            type="poll_single",
            question="What's your experience level?",
            options=["Beginner", "Intermediate", "Advanced"],
            required=True,
        )
        assert field.id == "field-1"
        assert field.type == "poll_single"
        assert len(field.options) == 3
        assert field.required is True

        # Test poll_multiple
        field_multi = CustomField(
            id="field-2",
            type="poll_multiple",
            question="Which technologies do you know?",
            options=["Python", "JavaScript", "AWS", "Docker"],
            required=False,
        )
        assert field_multi.type == "poll_multiple"
        assert field_multi.required is False

    def test_custom_field_invalid_type(self):
        """Test that invalid field types are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CustomField(
                id="field-1",
                type="invalid_type",
                question="Test question",
                options=["Option 1", "Option 2"],
                required=True,
            )
        assert "Input should be 'poll_single' or 'poll_multiple'" in str(exc_info.value)

    def test_custom_field_duplicate_options(self):
        """Test that duplicate options are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CustomField(
                id="field-1",
                type="poll_single",
                question="Test question",
                options=["Option 1", "Option 1", "Option 2"],  # Duplicate
                required=True,
            )
        assert "Poll options must be unique" in str(exc_info.value)

    def test_custom_field_question_length_validation(self):
        """Test question length constraints"""
        # Test empty question
        with pytest.raises(ValidationError):
            CustomField(
                id="field-1",
                type="poll_single",
                question="",  # Empty question
                options=["Option 1", "Option 2"],
                required=True,
            )

        # Test very long question
        with pytest.raises(ValidationError):
            CustomField(
                id="field-1",
                type="poll_single",
                question="x" * 501,  # Exceeds 500 char limit
                options=["Option 1", "Option 2"],
                required=True,
            )

    def test_custom_field_options_constraints(self):
        """Test options array constraints"""
        # Test too few options
        with pytest.raises(ValidationError):
            CustomField(
                id="field-1",
                type="poll_single",
                question="Test question",
                options=["Only one option"],  # Need at least 2
                required=True,
            )

        # Test too many options
        with pytest.raises(ValidationError):
            CustomField(
                id="field-1",
                type="poll_single",
                question="Test question",
                options=[f"Option {i}" for i in range(1, 12)],  # 11 options, max is 10
                required=True,
            )


class TestProjectImageModel:
    """Test ProjectImage model validation"""

    def test_valid_project_image_creation(self):
        """Test creating valid project images"""
        image = ProjectImage(
            url="https://s3.amazonaws.com/bucket/image.jpg",
            filename="image.jpg",
            size=1024000,  # 1MB
        )
        assert image.url.startswith("https://")
        assert image.filename == "image.jpg"
        assert image.size == 1024000

    def test_project_image_invalid_url(self):
        """Test that invalid URLs are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ProjectImage(url="invalid-url", filename="image.jpg", size=1024000)
        assert "Invalid image URL format" in str(exc_info.value)

    def test_project_image_file_size_limits(self):
        """Test file size constraints"""
        # Test zero size
        with pytest.raises(ValidationError):
            ProjectImage(
                url="https://s3.amazonaws.com/bucket/image.jpg",
                filename="image.jpg",
                size=0,  # Invalid size
            )

        # Test too large
        with pytest.raises(ValidationError):
            ProjectImage(
                url="https://s3.amazonaws.com/bucket/image.jpg",
                filename="image.jpg",
                size=15_000_000,  # 15MB - exceeds 10MB limit
            )

    def test_project_image_filename_validation(self):
        """Test filename constraints"""
        # Test empty filename
        with pytest.raises(ValidationError):
            ProjectImage(
                url="https://s3.amazonaws.com/bucket/image.jpg",
                filename="",  # Empty filename
                size=1024000,
            )

        # Test very long filename
        with pytest.raises(ValidationError):
            ProjectImage(
                url="https://s3.amazonaws.com/bucket/image.jpg",
                filename="x" * 256,  # Exceeds 255 char limit
                size=1024000,
            )


class TestFormSchemaModel:
    """Test FormSchema model validation"""

    def test_valid_form_schema_creation(self):
        """Test creating valid form schemas"""
        custom_field = CustomField(
            id="field-1",
            type="poll_single",
            question="Test question",
            options=["Option 1", "Option 2"],
            required=True,
        )

        schema = FormSchema(
            version="1.0",
            fields=[custom_field],
            richTextDescription="# Test Description\n\nThis is **markdown**.",
        )

        assert schema.version == "1.0"
        assert len(schema.fields) == 1
        assert schema.richTextDescription.startswith("# Test Description")

    def test_form_schema_unique_field_ids(self):
        """Test that field IDs must be unique"""
        field1 = CustomField(
            id="duplicate-id",
            type="poll_single",
            question="Question 1",
            options=["A", "B"],
            required=True,
        )

        field2 = CustomField(
            id="duplicate-id",  # Same ID
            type="poll_multiple",
            question="Question 2",
            options=["C", "D"],
            required=False,
        )

        with pytest.raises(ValidationError) as exc_info:
            FormSchema(version="1.0", fields=[field1, field2])
        assert "Field IDs must be unique" in str(exc_info.value)

    def test_form_schema_max_fields_limit(self):
        """Test maximum fields constraint"""
        fields = []
        for i in range(21):  # Create 21 fields (exceeds limit of 20)
            fields.append(
                CustomField(
                    id=f"field-{i}",
                    type="poll_single",
                    question=f"Question {i}",
                    options=["A", "B"],
                    required=False,
                )
            )

        with pytest.raises(ValidationError):
            FormSchema(version="1.0", fields=fields)

    def test_form_schema_rich_text_length_limit(self):
        """Test rich text description length constraint"""
        custom_field = CustomField(
            id="field-1",
            type="poll_single",
            question="Test question",
            options=["A", "B"],
            required=True,
        )

        with pytest.raises(ValidationError):
            FormSchema(
                version="1.0",
                fields=[custom_field],
                richTextDescription="x" * 10001,  # Exceeds 10000 char limit
            )


class TestProjectSubmissionModels:
    """Test project submission models"""

    def test_project_submission_create_model(self):
        """Test ProjectSubmissionCreate model"""
        submission = ProjectSubmissionCreate(
            projectId="project-123",
            personId="person-456",
            responses={"field-1": "Answer 1", "field-2": ["Option A", "Option B"]},
        )

        assert submission.projectId == "project-123"
        assert submission.personId == "person-456"
        assert submission.responses["field-1"] == "Answer 1"
        assert isinstance(submission.responses["field-2"], list)

    def test_project_submission_complete_model(self):
        """Test complete ProjectSubmission model"""
        now = datetime.now()
        submission = ProjectSubmission(
            id="submission-123",
            projectId="project-123",
            personId="person-456",
            responses={"field-1": "Answer 1"},
            createdAt=now,
            updatedAt=now,
        )

        assert submission.id == "submission-123"
        assert submission.createdAt == now
        assert submission.updatedAt == now


class TestEnhancedProjectModels:
    """Test enhanced project models with dynamic forms support"""

    def test_enhanced_project_create_model(self):
        """Test EnhancedProjectCreate model"""
        custom_field = CustomField(
            id="field-1",
            type="poll_single",
            question="Experience level?",
            options=["Beginner", "Advanced"],
            required=True,
        )

        form_schema = FormSchema(
            version="1.0", fields=[custom_field], richTextDescription="# Description"
        )

        image = ProjectImage(
            url="https://s3.amazonaws.com/bucket/image.jpg",
            filename="image.jpg",
            size=1024000,
        )

        project = EnhancedProjectCreate(
            name="Test Project",
            description="Test description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            customFields=[custom_field],
            formSchema=form_schema,
            images=[image],
        )

        assert project.name == "Test Project"
        assert len(project.customFields) == 1
        assert project.formSchema.version == "1.0"
        assert len(project.images) == 1

    def test_enhanced_project_complete_model(self):
        """Test complete EnhancedProject model"""
        now = datetime.now()
        project = EnhancedProject(
            id="project-123",
            name="Test Project",
            description="Test description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            createdAt=now,
            updatedAt=now,
            currentParticipants=5,
        )

        assert project.id == "project-123"
        assert project.currentParticipants == 5
        assert project.createdAt == now

    def test_enhanced_project_optional_fields(self):
        """Test that enhanced fields are optional"""
        # Should work without dynamic form fields
        project = EnhancedProjectCreate(
            name="Simple Project",
            description="Simple description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=50,
        )

        assert project.customFields is None
        assert project.formSchema is None
        assert project.images is None

    def test_enhanced_project_validation_constraints(self):
        """Test enhanced project validation constraints"""
        # Test invalid date format would be handled by existing validation
        # Test invalid maxParticipants
        with pytest.raises(ValidationError):
            EnhancedProjectCreate(
                name="Test Project",
                description="Test description",
                startDate="2025-01-01",
                endDate="2025-12-31",
                maxParticipants=0,  # Should be >= 1
            )

        # Test invalid name length
        with pytest.raises(ValidationError):
            EnhancedProjectCreate(
                name="",  # Empty name
                description="Test description",
                startDate="2025-01-01",
                endDate="2025-12-31",
                maxParticipants=50,
            )
