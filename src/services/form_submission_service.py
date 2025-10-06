"""
Form Submission Service - Business logic for form submissions
Orchestrates repository operations and implements validation rules
"""

from typing import List, Optional
from ..repositories.project_submissions_repository import ProjectSubmissionsRepository
from ..models.dynamic_forms import (
    ProjectSubmissionCreate,
    ProjectSubmission,
    FormSchema,
)
from datetime import datetime


class FormSubmissionService:
    """Service for form submission business logic"""

    def __init__(self, submissions_repository: ProjectSubmissionsRepository):
        self.submissions_repository = submissions_repository

    def submit_form_responses(
        self, submission_data: ProjectSubmissionCreate
    ) -> ProjectSubmission:
        """Submit form responses with validation"""
        # Create submission in repository
        created_data = self.submissions_repository.create(submission_data.model_dump())

        # Convert to ProjectSubmission model
        return ProjectSubmission(
            id=created_data["id"],
            projectId=created_data["projectId"],
            personId=created_data["personId"],
            responses=created_data["responses"],
            createdAt=datetime.fromisoformat(created_data["createdAt"]),
            updatedAt=datetime.fromisoformat(created_data["updatedAt"]),
        )

    def validate_submission_against_schema(
        self, submission: ProjectSubmissionCreate, form_schema: FormSchema
    ) -> bool:
        """Validate submission against form schema"""
        for field in form_schema.fields:
            field_id = field.id

            # Check required fields
            if field.required and field_id not in submission.responses:
                raise ValueError(f"Required field '{field_id}' is missing")

            # Validate field values if present
            if field_id in submission.responses:
                response_value = submission.responses[field_id]

                if field.type == "poll_single":
                    if response_value not in field.options:
                        raise ValueError(
                            f"Invalid option '{response_value}' for field '{field_id}'"
                        )

                elif field.type == "poll_multiple":
                    if isinstance(response_value, list):
                        for value in response_value:
                            if value not in field.options:
                                raise ValueError(
                                    f"Invalid option '{value}' for field '{field_id}'"
                                )
                    else:
                        raise ValueError(f"Field '{field_id}' expects a list of values")

        return True

    def get_project_submissions(self, project_id: str) -> List[ProjectSubmission]:
        """Get all submissions for a project"""
        submissions_data = self.submissions_repository.get_by_project_id(project_id)

        return [
            ProjectSubmission(
                id=data["id"],
                projectId=data["projectId"],
                personId=data["personId"],
                responses=data["responses"],
                createdAt=datetime.fromisoformat(data["createdAt"]),
                updatedAt=datetime.fromisoformat(data["updatedAt"]),
            )
            for data in submissions_data
        ]

    def get_submission_by_person_and_project(
        self, person_id: str, project_id: str
    ) -> Optional[ProjectSubmission]:
        """Get specific submission by person and project"""
        submission_data = self.submissions_repository.get_by_person_and_project(
            person_id, project_id
        )

        if not submission_data:
            return None

        return ProjectSubmission(
            id=submission_data["id"],
            projectId=submission_data["projectId"],
            personId=submission_data["personId"],
            responses=submission_data["responses"],
            createdAt=datetime.fromisoformat(submission_data["createdAt"]),
            updatedAt=datetime.fromisoformat(submission_data["updatedAt"]),
        )
