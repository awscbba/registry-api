"""
Form Submissions router - handles form submission endpoints
Clean architecture implementation using service layer
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends

from ..models.dynamic_forms import ProjectSubmissionCreate, ProjectSubmission
from ..services.form_submission_service import FormSubmissionService
from ..services.service_registry_manager import get_form_submission_service
from ..utils.responses import (
    create_success_response,
    create_error_response,
    create_list_response,
)

router = APIRouter(prefix="/v2/form-submissions", tags=["Form Submissions"])


@router.post("", response_model=dict)
async def submit_form_responses(
    submission_data: ProjectSubmissionCreate,
    submission_service: FormSubmissionService = Depends(get_form_submission_service),
):
    """Submit form responses for a project."""
    try:
        submission = submission_service.submit_form_responses(submission_data)
        return create_success_response(submission.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", response_model=dict)
async def get_project_submissions(
    project_id: str,
    submission_service: FormSubmissionService = Depends(get_form_submission_service),
):
    """Get all submissions for a project."""
    try:
        submissions = submission_service.get_project_submissions(project_id)
        return create_list_response(
            [submission.model_dump() for submission in submissions], len(submissions)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/person/{person_id}/project/{project_id}", response_model=dict)
async def get_person_project_submission(
    person_id: str,
    project_id: str,
    submission_service: FormSubmissionService = Depends(get_form_submission_service),
):
    """Get specific submission by person and project."""
    try:
        submission = submission_service.get_submission_by_person_and_project(
            person_id, project_id
        )
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        return create_success_response(submission.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
