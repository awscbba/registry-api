"""
People router - handles all person-related endpoints.
Clean architecture implementation using service layer.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..models.person import PersonCreate, PersonUpdate, PersonResponse
from ..services.people_service import PeopleService
from ..services.service_registry_manager import get_people_service
from ..utils.responses import (
    create_success_response,
    create_error_response,
    create_list_response,
)

router = APIRouter(prefix="/v2/people", tags=["People"])


@router.get("/", response_model=dict)
async def list_people(
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of results"
    ),
    people_service: PeopleService = Depends(get_people_service),
) -> dict:
    """Get all people."""
    try:
        people = people_service.list_people(limit=limit)
        return create_list_response(people)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve people: {str(e)}"
        )


@router.get("/{person_id}", response_model=dict)
async def get_person(
    person_id: str, people_service: PeopleService = Depends(get_people_service)
) -> dict:
    """Get a specific person by ID."""
    try:
        person = people_service.get_person(person_id)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Get user roles from RBAC service
        from ..services.service_registry_manager import get_rbac_service

        rbac_service = get_rbac_service()
        user_roles = await rbac_service.get_user_roles(person_id)
        role_names = [role.value for role in user_roles]

        # Fallback: If no roles found but user is admin, assign admin role
        if (
            not role_names and person.isAdmin
            if hasattr(person, "isAdmin")
            else person.get("isAdmin", False)
        ):
            role_names = ["admin"]

        # Add roles to person data
        person_dict = person if isinstance(person, dict) else person.model_dump()
        person_dict["roles"] = role_names

        return create_success_response(person_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve person: {str(e)}"
        )


@router.post("/", response_model=dict, status_code=201)
async def create_person(
    person_data: PersonCreate,
    people_service: PeopleService = Depends(get_people_service),
) -> dict:
    """Create a new person."""
    try:
        person = people_service.create_person(person_data)
        return create_success_response(person, "Person created successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create person: {str(e)}"
        )


@router.put("/{person_id}", response_model=dict)
async def update_person(
    person_id: str,
    person_data: PersonUpdate,
    people_service: PeopleService = Depends(get_people_service),
) -> dict:
    """Update an existing person."""
    try:
        person = people_service.update_person(person_id, person_data)

        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return create_success_response(person, "Person updated successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update person: {str(e)}"
        )


@router.delete("/{person_id}", response_model=dict)
async def delete_person(
    person_id: str, people_service: PeopleService = Depends(get_people_service)
) -> dict:
    """Delete a person."""
    try:
        success = await people_service.delete_person(person_id, "system")

        if not success:
            raise HTTPException(status_code=404, detail="Person not found")

        return create_success_response({"deleted": True}, "Person deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete person: {str(e)}"
        )


@router.post("/check-email", response_model=dict)
async def check_email_exists(
    email_data: dict, people_service: PeopleService = Depends(get_people_service)
) -> dict:
    """Check if a person with the given email exists."""
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        exists = people_service.check_email_exists(email)
        return create_success_response({"exists": exists})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check email: {str(e)}")
