"""
Public router - handles public endpoints that don't require authentication.
"""

from fastapi import APIRouter, HTTPException, Depends

from ..services.subscriptions_service import SubscriptionsService
from ..services.service_registry_manager import get_subscriptions_service
from ..models.subscription import SubscriptionCreate
from ..utils.responses import create_success_response

router = APIRouter(prefix="/v2/public", tags=["public"])


@router.post("/subscribe", response_model=dict, status_code=201)
async def public_subscribe(
    subscription_data: dict,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Public subscription endpoint (no authentication required)."""
    try:
        # Convert dict to SubscriptionCreate model
        subscription_create = SubscriptionCreate(**subscription_data)

        subscription = await subscriptions_service.create_subscription(
            subscription_create
        )
        return create_success_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
