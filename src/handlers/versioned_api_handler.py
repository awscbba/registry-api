"""
Versioned API handler with v1 and v2 endpoints.
This allows us to deploy fixes safely while maintaining backward compatibility.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from ..models.person import PersonCreate, PersonResponse
from ..models.subscription import SubscriptionCreate
from ..models.auth import LoginRequest, LoginResponse
from ..services.dynamodb_service import DynamoDBService
from ..services.auth_service import AuthService
from ..utils.error_handler import StandardErrorHandler, handle_database_error
from ..utils.logging_config import get_handler_logger
from ..utils.response_models import (
    ResponseFactory,
    create_v1_response,
    create_v2_response,
)

# Configure standardized logging
logger = get_handler_logger("versioned_api")

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
auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
        logger.log_api_request("GET", "/v1/subscriptions")
        subscriptions = await db_service.get_all_subscriptions()

        response = create_v1_response(subscriptions)
        logger.log_api_response("GET", "/v1/subscriptions", 200)
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve subscriptions",
            operation="get_subscriptions_v1",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving subscriptions", e)


@v1_router.get("/projects")
async def get_projects_v1():
    """Get all projects (v1 - legacy version)."""
    try:
        logger.log_api_request("GET", "/v1/projects")
        projects = await db_service.get_all_projects()

        response = create_v1_response(projects)
        logger.log_api_response("GET", "/v1/projects", 200)
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve projects",
            operation="get_projects_v1",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving projects", e)


@v1_router.post("/public/subscribe")
async def create_subscription_v1(subscription_data: dict):
    """Create subscription (v1 - legacy version with known issues)."""
    # This is the original implementation with the bugs
    # Kept for backward compatibility
    try:
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

        # FIXED: Added proper await keywords for v1 compatibility
        existing_person = await db_service.get_person_by_email(person_create.email)

        if existing_person:
            # Use existing person - existing_person is a Person object
            person_id = existing_person.id
        else:
            # FIXED: Added proper await keyword
            created_person = await db_service.create_person(person_create)
            person_id = created_person.id

        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status="pending",  # Original status
            notes=notes,
        )

        # FIXED: Pass SubscriptionCreate object directly instead of dict
        created_subscription = await db_service.create_subscription(subscription_create)

        return {
            "message": "Subscription created successfully",
            "subscription": created_subscription,
            "person_created": existing_person is None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("creating subscription (v1)", e)


# ==================== V2 ENDPOINTS (Fixed) ====================


@v2_router.get("/subscriptions")
async def get_subscriptions_v2():
    """Get all subscriptions (v2 - enhanced version)."""
    try:
        logger.log_api_request("GET", "/v2/subscriptions")
        subscriptions = await db_service.get_all_subscriptions()

        response = create_v2_response(
            subscriptions, metadata={"total_count": len(subscriptions)}
        )
        logger.log_api_response(
            "GET",
            "/v2/subscriptions",
            200,
            additional_context={"count": len(subscriptions)},
        )
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve subscriptions",
            operation="get_subscriptions_v2",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving subscriptions", e)


@v2_router.get("/projects")
async def get_projects_v2():
    """Get all projects (v2 - enhanced version)."""
    try:
        logger.log_api_request("GET", "/v2/projects")
        projects = await db_service.get_all_projects()

        response = create_v2_response(projects, metadata={"total_count": len(projects)})
        logger.log_api_response(
            "GET", "/v2/projects", 200, additional_context={"count": len(projects)}
        )
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve projects",
            operation="get_projects_v2",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving projects", e)


@v2_router.post("/people/check-email")
async def check_person_exists_v2(email_data: dict):
    """Check if a person exists by email (v2)."""
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
            )

        existing_person = await db_service.get_person_by_email(email)

        return {"exists": existing_person is not None, "version": "v2"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking person existence (v2): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check person existence",
        )


@v2_router.post("/subscriptions/check")
async def check_subscription_exists_v2(check_data: dict):
    """Check if a person is already subscribed to a project (v2)."""
    try:
        email = check_data.get("email")
        project_id = check_data.get("projectId")

        if not email or not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and projectId are required",
            )

        # Get person by email
        existing_person = await db_service.get_person_by_email(email)
        if not existing_person:
            return {"subscribed": False, "version": "v2"}

        # Check if subscription exists
        subscriptions = await db_service.get_subscriptions_by_person(existing_person.id)
        project_subscriptions = [
            sub for sub in subscriptions if sub.get("projectId") == project_id
        ]

        return {
            "subscribed": len(project_subscriptions) > 0,
            "subscription_status": (
                project_subscriptions[0].get("status")
                if project_subscriptions
                else None
            ),
            "version": "v2",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking subscription (v2): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check subscription",
        )


@v2_router.post("/public/subscribe", status_code=status.HTTP_201_CREATED)
async def create_subscription_v2(subscription_data: dict):
    """Create subscription (v2 - fixed version with proper async/await)."""
    try:
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
            status="pending",  # Requires administrator approval before activation
            notes=notes,
        )

        # FIXED: Pass SubscriptionCreate object directly instead of dict
        created_subscription = await db_service.create_subscription(subscription_create)

        return {
            "message": "Subscription created successfully",
            "subscription": created_subscription,
            "person_created": existing_person is None,
            "version": "v2",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("creating subscription (v2)", e)


# ==================== AUTH ENDPOINTS ====================


@auth_router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request):
    """
    Authenticate user and return JWT tokens.

    This endpoint handles admin and user authentication.
    """
    try:
        logger.log_api_request("POST", "/auth/login", {"email": login_request.email})

        # Get client IP and user agent for security logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Authenticate user
        success, login_response, error_message = await auth_service.authenticate_user(
            login_request, client_ip, user_agent
        )

        if not success:
            logger.log_api_response(
                "POST", "/auth/login", 401, {"error": error_message}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=error_message
            )

        logger.log_api_response(
            "POST", "/auth/login", 200, {"user_id": login_response.user["id"]}
        )
        return login_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Authentication error",
            operation="login",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


@auth_router.get("/me")
async def get_current_user_info(request: Request):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    try:
        from ..middleware.auth_middleware import get_current_user
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Get current user using auth middleware
        from ..middleware.auth_middleware import auth_middleware

        current_user = await auth_middleware.get_current_user(credentials)

        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "firstName": current_user.first_name,
                "lastName": current_user.last_name,
                "requirePasswordChange": current_user.require_password_change,
                "isActive": current_user.is_active,
                "lastLoginAt": (
                    current_user.last_login_at.isoformat()
                    if current_user.last_login_at
                    else None
                ),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting current user info",
            operation="get_current_user_info",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve user information",
        )


@auth_router.post("/logout")
async def logout(request: Request):
    """
    Logout user (invalidate token).

    Note: With JWT tokens, logout is typically handled client-side by removing the token.
    This endpoint is provided for consistency and future token blacklisting if needed.
    """
    try:
        # For now, just return success since JWT tokens are stateless
        # In the future, we could implement token blacklisting here

        return {
            "message": "Logged out successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(
            "Error during logout",
            operation="logout",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout error"
        )


@v2_router.get("/admin/test")
async def test_admin_system():
    """Test endpoint to verify admin system is working."""
    try:
        # Get a test admin user (configurable via environment)
        import os

        test_admin_email = os.getenv("TEST_ADMIN_EMAIL", "admin@awsugcbba.org")
        person = await db_service.get_person_by_email(test_admin_email)
        if not person:
            return {"error": "Admin user not found", "version": "v2"}

        return {
            "message": "Admin system test successful",
            "admin_user": {
                "id": person.id,
                "email": person.email,
                "firstName": person.first_name,
                "lastName": person.last_name,
                "isAdmin": person.is_admin,
            },
            "version": "v2",
        }

    except Exception as e:
        logger.error(f"Error testing admin system: {str(e)}")
        return {"error": str(e), "version": "v2"}


@v2_router.get("/admin/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard data with statistics and recent activity."""
    try:
        logger.log_api_request("GET", "/v2/admin/dashboard")
        
        # Get statistics from database
        projects = await db_service.get_all_projects()
        subscriptions = await db_service.get_all_subscriptions()
        
        # Count active projects
        active_projects = [p for p in projects if p.get('status') == 'active']
        
        # Count active subscriptions
        active_subscriptions = [s for s in subscriptions if s.get('status') == 'active']
        
        # Get recent activity (last 10 subscriptions)
        recent_subscriptions = sorted(
            subscriptions, 
            key=lambda x: x.get('createdAt', ''), 
            reverse=True
        )[:10]
        
        # Create dashboard data
        dashboard_data = {
            "totalProjects": len(projects),
            "activeProjects": len(active_projects),
            "totalSubscriptions": len(subscriptions),
            "activeSubscriptions": len(active_subscriptions),
            "pendingSubscriptions": len([s for s in subscriptions if s.get('status') == 'pending']),
            "recentActivity": recent_subscriptions,
            "statistics": {
                "projectsCreatedThisMonth": len([p for p in projects if p.get('createdAt', '').startswith('2025-08')]),
                "subscriptionsThisMonth": len([s for s in subscriptions if s.get('createdAt', '').startswith('2025-08')]),
                "averageSubscriptionsPerProject": len(subscriptions) / max(len(projects), 1)
            }
        }
        
        response = create_v2_response(dashboard_data)
        logger.log_api_response("GET", "/v2/admin/dashboard", 200)
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get admin dashboard",
            operation="get_admin_dashboard",
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting admin dashboard", e)


@v2_router.get("/admin/people")
async def get_admin_people():
    """Get all people for admin management (v2)."""
    try:
        logger.log_api_request("GET", "/v2/admin/people")
        
        # Get all people from database
        people = await db_service.get_all_people()
        
        # Convert to admin-friendly format with additional fields
        admin_people = []
        for person in people:
            admin_person = {
                "id": person.id,
                "email": person.email,
                "firstName": person.first_name,
                "lastName": person.last_name,
                "phone": person.phone,
                "dateOfBirth": person.date_of_birth,
                "address": person.address.dict() if person.address else None,
                "isAdmin": person.is_admin,
                "createdAt": person.created_at.isoformat() if person.created_at else None,
                "updatedAt": person.updated_at.isoformat() if person.updated_at else None,
                # Add security fields for admin view
                "isActive": getattr(person, 'is_active', True),
                "requirePasswordChange": getattr(person, 'require_password_change', False),
                "lastLoginAt": getattr(person, 'last_login_at', None),
                "failedLoginAttempts": getattr(person, 'failed_login_attempts', 0)
            }
            admin_people.append(admin_person)
        
        response = create_v2_response(admin_people)
        logger.log_api_response("GET", "/v2/admin/people", 200)
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get admin people",
            operation="get_admin_people",
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting admin people", e)


@v2_router.get("/admin/projects")
async def get_admin_projects():
    """Get all projects for admin management with enhanced details (v2)."""
    try:
        logger.log_api_request("GET", "/v2/admin/projects")
        
        # Get all projects
        projects = await db_service.get_all_projects()
        
        # Get subscription counts for each project
        subscriptions = await db_service.get_all_subscriptions()
        
        # Enhance projects with subscription statistics
        enhanced_projects = []
        for project in projects:
            project_subscriptions = [s for s in subscriptions if s.get('projectId') == project.get('id')]
            
            enhanced_project = {
                **project,
                "subscriptionCount": len(project_subscriptions),
                "activeSubscriptions": len([s for s in project_subscriptions if s.get('status') == 'active']),
                "pendingSubscriptions": len([s for s in project_subscriptions if s.get('status') == 'pending']),
                "availableSlots": max(0, project.get('maxParticipants', 0) - len([s for s in project_subscriptions if s.get('status') == 'active'])) if project.get('maxParticipants') else None
            }
            enhanced_projects.append(enhanced_project)
        
        response = create_v2_response(enhanced_projects)
        logger.log_api_response("GET", "/v2/admin/projects", 200)
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get admin projects",
            operation="get_admin_projects",
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting admin projects", e)


@v2_router.get("/admin/subscriptions")
async def get_admin_subscriptions():
    """Get all subscriptions for admin management with enhanced details (v2)."""
    try:
        logger.log_api_request("GET", "/v2/admin/subscriptions")
        
        # Get all subscriptions
        subscriptions = await db_service.get_all_subscriptions()
        
        # Get people and projects for enhanced details
        people = await db_service.get_all_people()
        projects = await db_service.get_all_projects()
        
        # Create lookup dictionaries
        people_dict = {p.id: p for p in people}
        projects_dict = {p.get('id'): p for p in projects}
        
        # Enhance subscriptions with person and project details
        enhanced_subscriptions = []
        for subscription in subscriptions:
            person = people_dict.get(subscription.get('personId'))
            project = projects_dict.get(subscription.get('projectId'))
            
            enhanced_subscription = {
                **subscription,
                "person": {
                    "id": person.id,
                    "email": person.email,
                    "firstName": person.first_name,
                    "lastName": person.last_name
                } if person else None,
                "project": {
                    "id": project.get('id'),
                    "name": project.get('name'),
                    "status": project.get('status')
                } if project else None
            }
            enhanced_subscriptions.append(enhanced_subscription)
        
        response = create_v2_response(enhanced_subscriptions)
        logger.log_api_response("GET", "/v2/admin/subscriptions", 200)
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get admin subscriptions",
            operation="get_admin_subscriptions",
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting admin subscriptions", e)


# Register the routers
app.include_router(v1_router)
app.include_router(v2_router)
app.include_router(auth_router)


# Legacy endpoints (unversioned) - redirect to v1 for compatibility
@app.get("/subscriptions")
async def get_subscriptions_legacy():
    """Legacy endpoint - redirects to v1."""
    return await get_subscriptions_v1()


@app.get("/projects")
async def get_projects_legacy():
    """Legacy endpoint - redirects to v2 for better functionality."""
    return await get_projects_v2()


@app.get("/admin/dashboard")
async def get_admin_dashboard_legacy():
    """Legacy admin dashboard endpoint - redirects to v2."""
    return await get_admin_dashboard()


@app.post("/public/subscribe")
async def create_subscription_legacy(subscription_data: dict):
    """Legacy endpoint - redirects to v1."""
    return await create_subscription_v1(subscription_data)


# ==================== AUTH ENDPOINTS ====================


# ==================== V2 PEOPLE ENDPOINTS ====================


@v2_router.get("/people")
async def get_people_v2(email: str = None):
    """Get people with optional email filter (v2)."""
    try:
        if email:
            # Query by email using EmailIndex GSI
            person = await db_service.get_person_by_email(email)
            if person:
                return {
                    "people": [person.dict()],
                    "version": "v2",
                    "count": 1,
                    "query": {"email": email},
                }
            else:
                return {
                    "people": [],
                    "version": "v2",
                    "count": 0,
                    "query": {"email": email},
                }
        else:
            # Get all people (limit for performance)
            people = await db_service.get_all_people(limit=100)
            return {
                "people": [person.dict() for person in people],
                "version": "v2",
                "count": len(people),
            }
    except Exception as e:
        raise handle_database_error("getting people (v2)", e)


@v2_router.put("/people/{person_id}/admin")
async def update_admin_status(person_id: str, admin_data: dict):
    """Update admin status for a person (admin only)."""
    try:
        # TODO: Add proper authentication middleware to verify admin user
        # For now, we'll implement basic validation

        is_admin = admin_data.get("isAdmin", False)

        # Get the person to update
        person = await db_service.get_person_by_id(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Update admin status
        update_data = {"isAdmin": is_admin}
        updated_person = await db_service.update_person(person_id, update_data)

        return {
            "message": f"Admin status {'granted' if is_admin else 'revoked'} successfully",
            "person": {
                "id": updated_person.id,
                "email": updated_person.email,
                "firstName": updated_person.first_name,
                "lastName": updated_person.last_name,
                "isAdmin": updated_person.is_admin,
            },
            "version": "v2",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("updating admin status", e)
