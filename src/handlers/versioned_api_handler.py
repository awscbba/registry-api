"""
Versioned API handler with v1 and v2 endpoints.
This allows us to deploy fixes safely while maintaining backward compatibility.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from ..models.person import PersonCreate, PersonResponse
from ..models.subscription import SubscriptionCreate
from ..services.dynamodb_service import DynamoDBService
from ..services.auth_service import AuthService
from ..middleware.auth_middleware import get_current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
db_service = DynamoDBService()
auth_service = AuthService()

# Create FastAPI app
app = FastAPI(
    title="People Register API - Versioned",
    description="""
    ## People Register API with Versioning

    This API supports multiple versions to ensure backward compatibility while allowing for improvements.

    ### Available Versions
    - **v1**: Current stable version (legacy endpoints)
    - **v2**: Enhanced version with bug fixes and improvements

    ### Version Strategy
    - v1 endpoints maintain current behavior for compatibility
    - v2 endpoints include latest fixes and improvements
    - New features will be added to the latest version
    """,
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create version-specific routers
v1_router = APIRouter(prefix="/v1", tags=["v1"])
v2_router = APIRouter(prefix="/v2", tags=["v2"])


# Health check endpoint (unversioned)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "people-register-api-versioned",
        "timestamp": datetime.now().isoformat(),
        "versions": ["v1", "v2"],
    }


# ==================== V1 ENDPOINTS (Legacy) ====================


@v1_router.get("/subscriptions")
async def get_subscriptions_v1():
    """Get all subscriptions (v1 - legacy version)."""
    try:
        subscriptions = db_service.get_all_subscriptions()
        return {"subscriptions": subscriptions}
    except Exception as e:
        logger.error(f"Error getting subscriptions (v1): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions",
        )


@v1_router.get("/projects")
async def get_projects_v1():
    """Get all projects (v1 - legacy version)."""
    try:
        projects = db_service.get_all_projects()
        return {"projects": projects}
    except Exception as e:
        logger.error(f"Error getting projects (v1): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects",
        )


@v1_router.post("/public/subscribe")
async def create_subscription_v1(subscription_data: dict):
    """Create subscription (v1 - legacy version with known issues)."""
    # This is the original implementation with the bugs
    # Kept for backward compatibility
    try:
        from ..models.person import PersonCreate
        from ..models.subscription import SubscriptionCreate

        person_data = subscription_data.get("person")
        project_id = subscription_data.get("projectId")
        notes = subscription_data.get("notes")

        if not person_data or not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both person data and projectId are required",
            )

        # Handle person data for public subscriptions (v1 - legacy behavior)
        # Convert 'name' field to firstName/lastName if provided
        if "name" in person_data and "firstName" not in person_data:
            name_parts = person_data["name"].strip().split(" ", 1)
            person_data["firstName"] = name_parts[0]
            person_data["lastName"] = name_parts[1] if len(name_parts) > 1 else ""
            # Remove the 'name' field as it's not part of PersonCreate
            person_data = {k: v for k, v in person_data.items() if k != "name"}

        # Set default values for required fields if not provided
        person_data.setdefault("phone", "")
        person_data.setdefault("dateOfBirth", "1990-01-01")  # Default date
        person_data.setdefault(
            "address",
            {"street": "", "city": "", "state": "", "zipCode": "", "country": ""},
        )

        # Validate person data
        person_create = PersonCreate(**person_data)

        # Verify project exists (this method is NOT async)
        project = db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found"
            )

        # NOTE: This version has the original bugs for compatibility
        # Missing await keywords and wrong parameter types
        existing_person = db_service.get_person_by_email(
            person_create.email
        )  # Missing await

        if existing_person:
            person_id = (
                existing_person.id
                if hasattr(existing_person, "id")
                else existing_person.get("id")
            )
        else:
            created_person = db_service.create_person(person_create)  # Missing await
            person_id = created_person.id

        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status="pending",  # Original status
            notes=notes,
        )

        # Original implementation passed dict instead of object
        subscription_dict = subscription_create.model_dump()
        created_subscription = db_service.create_subscription(subscription_dict)

        return {
            "message": "Subscription created successfully",
            "subscription": created_subscription,
            "person_created": existing_person is None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription (v1): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )


# ==================== V2 ENDPOINTS (Fixed) ====================


@v2_router.get("/subscriptions")
async def get_subscriptions_v2():
    """Get all subscriptions (v2 - enhanced version)."""
    try:
        subscriptions = db_service.get_all_subscriptions()
        return {
            "subscriptions": subscriptions,
            "version": "v2",
            "count": len(subscriptions),
        }
    except Exception as e:
        logger.error(f"Error getting subscriptions (v2): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions",
        )


@v2_router.get("/projects")
async def get_projects_v2():
    """Get all projects (v2 - enhanced version)."""
    try:
        projects = db_service.get_all_projects()
        return {"projects": projects, "version": "v2", "count": len(projects)}
    except Exception as e:
        logger.error(f"Error getting projects (v2): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects",
        )


@v2_router.post("/public/subscribe", status_code=status.HTTP_201_CREATED)
async def create_subscription_v2(subscription_data: dict):
    """Create subscription (v2 - fixed version with proper async/await)."""
    try:
        from ..models.person import PersonCreate
        from ..models.subscription import SubscriptionCreate

        # Extract person and subscription data
        person_data = subscription_data.get("person")
        project_id = subscription_data.get("projectId")
        notes = subscription_data.get("notes")

        if not person_data or not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both person data and projectId are required",
            )

        # Handle person data for public subscriptions
        # Convert 'name' field to firstName/lastName if provided
        if "name" in person_data and "firstName" not in person_data:
            name_parts = person_data["name"].strip().split(" ", 1)
            person_data["firstName"] = name_parts[0]
            person_data["lastName"] = name_parts[1] if len(name_parts) > 1 else ""
            # Remove the 'name' field as it's not part of PersonCreate
            person_data = {k: v for k, v in person_data.items() if k != "name"}

        # Set default values for required fields if not provided
        person_data.setdefault("phone", "")
        person_data.setdefault("dateOfBirth", "1990-01-01")  # Default date
        person_data.setdefault(
            "address",
            {"street": "", "city": "", "state": "", "zipCode": "", "country": ""},
        )

        # Validate person data
        person_create = PersonCreate(**person_data)

        # Verify project exists (this method is NOT async)
        project = db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found"
            )

        # FIXED: Added proper await keywords
        existing_person = await db_service.get_person_by_email(person_create.email)

        if existing_person:
            # Use existing person - existing_person is a Person object
            person_id = existing_person.id
        else:
            # FIXED: Added proper await keyword
            created_person = await db_service.create_person(person_create)
            person_id = created_person.id

        # Create subscription
        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status="active",  # FIXED: Changed from "pending" to "active"
            notes=notes,
        )

        # FIXED: Pass SubscriptionCreate object directly instead of dict
        created_subscription = db_service.create_subscription(subscription_create)

        return {
            "message": "Subscription created successfully",
            "subscription": created_subscription,
            "person_created": existing_person is None,
            "version": "v2",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription (v2): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )


# Register the routers
app.include_router(v1_router)
app.include_router(v2_router)


# Legacy endpoints (unversioned) - redirect to v1 for compatibility
@app.get("/subscriptions")
async def get_subscriptions_legacy():
    """Legacy endpoint - redirects to v1."""
    return await get_subscriptions_v1()


@app.get("/projects")
async def get_projects_legacy():
    """Legacy endpoint - redirects to v1."""
    return await get_projects_v1()


@app.post("/public/subscribe")
async def create_subscription_legacy(subscription_data: dict):
    """Legacy endpoint - redirects to v1."""
    return await create_subscription_v1(subscription_data)
