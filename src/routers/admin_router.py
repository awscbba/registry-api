"""
Admin router with clean, standardized endpoints.
All fields use camelCase - no mapping complexity.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..services.admin_service import AdminService
from ..services.people_service import PeopleService
from ..services.subscriptions_service import SubscriptionsService
from ..services.service_registry_manager import (
    get_admin_service,
    get_people_service,
    get_subscriptions_service,
)
from ..models.auth import User
from ..models.person import PersonCreate, PersonUpdate, PersonResponse
from ..routers.auth_router import require_admin, get_current_user
from ..utils.responses import create_success_response, create_error_response

router = APIRouter(prefix="/v2/admin", tags=["admin"])


@router.get("/dashboard", response_model=dict)
async def get_dashboard_data(
    current_user: User = Depends(require_admin),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get admin dashboard data."""
    try:
        dashboard_data = await admin_service.get_dashboard_data()
        return create_success_response(dashboard_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/enhanced", response_model=dict)
async def get_enhanced_dashboard(
    current_user: User = Depends(require_admin),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get enhanced admin dashboard data."""
    try:
        enhanced_data = await admin_service.get_enhanced_dashboard_data()
        return create_success_response(enhanced_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=dict)
async def get_admin_analytics(
    current_user: User = Depends(require_admin),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Get detailed analytics data."""
    try:
        analytics_data = await admin_service.get_analytics_data()
        return create_success_response(analytics_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# User Management Endpoints
@router.get("/users", response_model=dict)
async def list_users(
    search: Optional[str] = Query(None, description="Search term for users"),
    limit: Optional[int] = Query(None, description="Maximum number of users to return"),
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """List all users (admin endpoint)."""
    try:
        users = await people_service.list_people(limit=limit)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            users = [
                user
                for user in users
                if (
                    search_lower in user.firstName.lower()
                    or search_lower in user.lastName.lower()
                    or search_lower in user.email.lower()
                )
            ]

        return create_success_response(users)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Get user by ID (admin endpoint)."""
    try:
        user = await people_service.get_person(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return create_success_response(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", response_model=dict)
async def create_user(
    user_data: PersonCreate,
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Create new user (admin endpoint)."""
    try:
        user = await people_service.create_person(user_data)
        return create_success_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    user_data: PersonUpdate,
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Update user (admin endpoint)."""
    try:
        user = await people_service.update_person(user_id, user_data)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return create_success_response(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Delete user (admin endpoint)."""
    try:
        success = await people_service.delete_person(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        return create_success_response({"deleted": True, "userId": user_id})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/bulk-action", response_model=dict)
async def bulk_user_action(
    bulk_data: dict,
    current_user: User = Depends(require_admin),
    admin_service: AdminService = Depends(get_admin_service),
):
    """Execute bulk action on users."""
    try:
        results = await admin_service.execute_bulk_action(bulk_data)
        return create_success_response(results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Admin aliases for people and subscriptions
@router.get("/people", response_model=dict)
async def get_admin_people(
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Get all people (admin alias)."""
    try:
        people = await people_service.list_people()
        return create_success_response(people)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/people/{person_id}", response_model=dict)
async def edit_admin_person(
    person_id: str,
    person_data: PersonUpdate,
    current_user: User = Depends(require_admin),
    people_service: PeopleService = Depends(get_people_service),
):
    """Edit person (admin endpoint)."""
    try:
        person = await people_service.update_person(person_id, person_data)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        return create_success_response(person)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions", response_model=dict)
async def get_admin_subscriptions(
    current_user: User = Depends(require_admin),
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get all subscriptions (admin endpoint)."""
    try:
        subscriptions = await subscriptions_service.list_subscriptions()
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registrations", response_model=dict)
async def get_admin_registrations(
    current_user: User = Depends(require_admin),
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get all registrations (alias for subscriptions)."""
    try:
        subscriptions = await subscriptions_service.list_subscriptions()
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test", response_model=dict)
async def test_admin_system(current_user: User = Depends(require_admin)):
    """Test admin system functionality."""
    return create_success_response(
        {
            "message": "Admin system working",
            "user": current_user.email,
            "timestamp": "2025-01-27T00:00:00Z",
        }
    )
