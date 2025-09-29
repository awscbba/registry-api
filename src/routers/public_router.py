"""
Public router - handles public endpoints that don't require authentication.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.subscriptions_service import SubscriptionsService
from ..services.people_service import PeopleService
from ..services.service_registry_manager import (
    get_subscriptions_service,
    get_people_service,
    get_email_service,
    get_projects_service,
)
from ..services.subscriptions_service import SubscriptionsService
from ..services.people_service import PeopleService
from ..services.email_service import EmailService
from ..services.projects_service import ProjectsService
from ..models.subscription import SubscriptionCreate
from ..models.person import PersonCreate
from ..utils.responses import create_success_response

router = APIRouter(prefix="/v2/public", tags=["public"])


class PublicSubscriptionRequest(BaseModel):
    """Schema for public subscription requests using email."""

    email: str = Field(..., description="Email address of the person subscribing")
    projectId: str = Field(..., description="ID of the project to subscribe to")
    firstName: str = Field(..., description="First name of the person")
    lastName: str = Field(..., description="Last name of the person")
    phone: str = Field(default="", description="Phone number (optional)")
    dateOfBirth: str = Field(
        default="1990-01-01", description="Date of birth (YYYY-MM-DD format)"
    )
    address: dict = Field(
        default_factory=lambda: {
            "street": "",
            "city": "",
            "state": "",
            "postalCode": "",
            "country": "",
        },
        description="Address information (optional)",
    )


@router.post("/subscribe", response_model=dict, status_code=201)
async def public_subscribe(
    subscription_data: PublicSubscriptionRequest,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
    people_service: PeopleService = Depends(get_people_service),
    email_service: EmailService = Depends(get_email_service),
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Public subscription endpoint (no authentication required)."""
    try:
        # Get project details for email
        project = await projects_service.get_project(subscription_data.projectId)
        project_name = project.name if project else "Unknown Project"

        # First, check if person exists by email
        existing_person = await people_service.get_person_by_email(
            subscription_data.email
        )

        person_created = False
        email_sent = False

        if existing_person:
            person_id = existing_person.id

            # Check if already subscribed BEFORE trying to create
            subscription_exists = subscriptions_service.check_subscription_exists(
                person_id, subscription_data.projectId
            )

            if subscription_exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"You are already subscribed to this project. Please check your email for project updates.",
                )

            # For existing users, create active subscription and send welcome email
            subscription_create = SubscriptionCreate(
                personId=person_id,
                projectId=subscription_data.projectId,
                status="active",  # Existing users get immediate active subscription
            )
            subscription = subscriptions_service.create_subscription(
                subscription_create
            )

            # Send welcome email to existing user
            email_result = await email_service.send_project_welcome_email(
                subscription_data.email, existing_person.firstName, project_name
            )
            email_sent = email_result.get("success", False)

        else:
            # Create new person
            try:
                from ..models.person import Address

                address = Address(**subscription_data.address)
                person_create = PersonCreate(
                    firstName=subscription_data.firstName,
                    lastName=subscription_data.lastName,
                    email=subscription_data.email,
                    phone=subscription_data.phone,
                    dateOfBirth=subscription_data.dateOfBirth,
                    address=address,
                    password="temp_password_123",  # Temporary password for public subscriptions
                    isAdmin=False,
                )
                new_person = await people_service.create_person(person_create)
                person_id = new_person.id
                person_created = True

                # For new users, create pending subscription and send pending email
                subscription_create = SubscriptionCreate(
                    personId=person_id,
                    projectId=subscription_data.projectId,
                    status="pending",  # New users get pending subscription
                )
                subscription = subscriptions_service.create_subscription(
                    subscription_create
                )

                # Send pending approval email to new user
                email_result = await email_service.send_subscription_pending_email(
                    subscription_data.email, subscription_data.firstName, project_name
                )
                email_sent = email_result.get("success", False)

            except Exception as e:
                # If person creation fails due to email already existing,
                # it means there's a race condition - try to get the person again
                if "already in use" in str(e) or "already exists" in str(e):
                    existing_person = await people_service.get_person_by_email(
                        subscription_data.email
                    )
                    if existing_person:
                        person_id = existing_person.id

                        # Check if already subscribed
                        subscription_exists = (
                            subscriptions_service.check_subscription_exists(
                                person_id, subscription_data.projectId
                            )
                        )

                        if subscription_exists:
                            raise HTTPException(
                                status_code=400,
                                detail=f"You are already subscribed to this project. Please check your email for project updates.",
                            )

                        # Create active subscription for existing user (race condition case)
                        subscription_create = SubscriptionCreate(
                            personId=person_id,
                            projectId=subscription_data.projectId,
                            status="active",
                        )
                        subscription = subscriptions_service.create_subscription(
                            subscription_create
                        )

                        # Send welcome email
                        email_result = await email_service.send_project_welcome_email(
                            subscription_data.email,
                            existing_person.firstName,
                            project_name,
                        )
                        email_sent = email_result.get("success", False)
                    else:
                        raise HTTPException(status_code=400, detail=str(e))
                else:
                    raise HTTPException(status_code=400, detail=str(e))

        return create_success_response(
            {
                "subscription": subscription,
                "personCreated": person_created,
                "emailSent": email_sent,
                "message": "Successfully subscribed to the project! Check your email for next steps.",
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle subscription already exists error
        if "already exists" in str(e):
            raise HTTPException(
                status_code=400,
                detail="You are already subscribed to this project. Please check your email for project updates.",
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your subscription: {str(e)}",
        )
