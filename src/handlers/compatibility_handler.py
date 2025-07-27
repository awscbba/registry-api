"""
Backward Compatibility Handler

This handler provides backward-compatible endpoints for the frontend
while the frontend is being updated to handle the new API format.
"""

from fastapi import FastAPI, HTTPException, status, Request, Depends
from typing import List
from ..models.person import PersonResponse
from ..services.dynamodb_service import DynamoDBService
from ..middleware.auth_middleware import get_current_user, require_no_password_change

app = FastAPI()
db_service = DynamoDBService()

@app.get("/people/legacy", response_model=List[PersonResponse])
async def list_people_legacy_format(
    request: Request,
    limit: int = 100,
    current_user=Depends(require_no_password_change)
):
    """
    Legacy endpoint that returns people as a direct array for backward compatibility.

    This endpoint maintains the old response format while the frontend is updated.
    Once frontend is updated, this endpoint can be removed.
    """
    try:
        people = await db_service.list_people(limit=limit)

        # Ensure we use PersonResponse to exclude sensitive fields
        return [PersonResponse.from_person(person) for person in people]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve people"
        )

@app.get("/people/new", response_model=dict)
async def list_people_new_format(
    request: Request,
    limit: int = 100,
    current_user=Depends(require_no_password_change)
):
    """
    New endpoint that returns people with metadata (count, pagination info, etc.)

    This is the new format that provides additional metadata.
    """
    try:
        people = await db_service.list_people(limit=limit)

        # Use PersonResponse to exclude sensitive fields
        people_response = [PersonResponse.from_person(person) for person in people]

        return {
            "people": people_response,
            "count": len(people_response),
            "limit": limit,
            "has_more": len(people_response) == limit  # Indicates if there might be more
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve people"
        )
