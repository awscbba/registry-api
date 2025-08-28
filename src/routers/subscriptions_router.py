"""
Subscriptions router with clean, standardized endpoints.
All fields use camelCase - no mapping complexity.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..services.subscriptions_service import SubscriptionsService
from ..services.service_registry_manager import get_subscriptions_service
from ..models.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
)
from ..utils.responses import create_success_response, create_error_response

router = APIRouter(prefix="/v2/subscriptions", tags=["subscriptions"])


@router.get("", response_model=dict)
async def list_subscriptions(
    limit: Optional[int] = Query(
        None, description="Maximum number of subscriptions to return"
    ),
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """List all subscriptions."""
    try:
        subscriptions = await subscriptions_service.list_subscriptions(limit=limit)
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}", response_model=dict)
async def get_subscription(
    subscription_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get a subscription by ID."""
    try:
        subscription = await subscriptions_service.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return create_success_response(subscription)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=dict)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Create a new subscription."""
    try:
        subscription = await subscriptions_service.create_subscription(
            subscription_data
        )
        return create_success_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{subscription_id}", response_model=dict)
async def update_subscription(
    subscription_id: str,
    updates: SubscriptionUpdate,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Update a subscription."""
    try:
        subscription = await subscriptions_service.update_subscription(
            subscription_id, updates
        )
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return create_success_response(subscription)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subscription_id}", response_model=dict)
async def delete_subscription(
    subscription_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Delete a subscription."""
    try:
        success = await subscriptions_service.delete_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return create_success_response({"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check", response_model=dict)
async def check_subscription_exists(
    check_data: dict,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Check if a subscription exists for a person and project."""
    try:
        person_id = check_data.get("personId")
        project_id = check_data.get("projectId")

        if not person_id or not project_id:
            raise HTTPException(
                status_code=400, detail="personId and projectId are required"
            )

        exists = await subscriptions_service.check_subscription_exists(
            person_id, project_id
        )
        return create_success_response({"exists": exists})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/person/{person_id}", response_model=dict)
async def get_person_subscriptions(
    person_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get all subscriptions for a person."""
    try:
        subscriptions = await subscriptions_service.get_person_subscriptions(person_id)
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", response_model=dict)
async def get_project_subscriptions(
    project_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get all subscriptions for a project."""
    try:
        subscriptions = await subscriptions_service.get_project_subscriptions(
            project_id
        )
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
