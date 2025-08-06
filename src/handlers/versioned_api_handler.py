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
from fastapi.security import HTTPAuthorizationCredentials

from ..models.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    AdminUnlockRequest,
    AdminUnlockResponse,
)
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.subscription import SubscriptionCreate, SubscriptionUpdate
from ..models.auth import LoginRequest, LoginResponse
from ..services.defensive_dynamodb_service import (
    DefensiveDynamoDBService as DynamoDBService,
)
from ..services.auth_service import AuthService
from ..services.email_service import email_service
from ..middleware.auth_middleware import get_current_user, auth_middleware
from ..utils.error_handler import StandardErrorHandler, handle_database_error
from ..utils.logging_config import get_handler_logger
from ..utils.password_utils import PasswordHasher
from ..utils.jwt_utils import JWTManager
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
            {"street": "", "city": "", "state": "", "postalCode": "", "country": ""},
        )

        # Validate person data
        person_create = PersonCreate(**person_data)

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
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
    """Create subscription (v2 - enhanced with password generation and email)."""
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
            {"street": "", "city": "", "state": "", "postalCode": "", "country": ""},
        )

        # Verify project exists and check subscription eligibility
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found"
            )

        # Check if project accepts new subscriptions
        project_status = project.get("status", "active")
        if project_status not in ["pending", "active"]:
            if project_status == "ongoing":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este proyecto está en curso y no acepta nuevas suscripciones. Contacte al administrador si necesita unirse.",
                )
            elif project_status == "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este proyecto ha sido completado y no acepta nuevas suscripciones.",
                )
            elif project_status == "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este proyecto ha sido cancelado y no acepta nuevas suscripciones.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este proyecto no está disponible para suscripciones.",
                )

        # Check project capacity if maxParticipants is set
        max_participants = project.get("maxParticipants")
        if max_participants and max_participants > 0:
            # Get current active subscriptions count
            project_subscriptions = await db_service.get_subscriptions_by_project(
                project_id
            )
            active_subscriptions = [
                sub for sub in project_subscriptions if sub.get("status") == "active"
            ]

            if len(active_subscriptions) >= max_participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Este proyecto ha alcanzado su capacidad máxima de {max_participants} participantes.",
                )

        # Check if person already exists
        try:
            existing_person = await db_service.get_person_by_email(person_data["email"])
        except Exception as email_error:
            logger.warning(f"Error checking existing person by email: {email_error}")
            existing_person = None

        person_created = False
        temporary_password = None

        if existing_person:
            # Use existing person
            person_id = existing_person.id
            logger.info(f"Using existing person: {person_id}")

            # Check for existing subscription before creating
            existing_subscription = await db_service.get_existing_subscription(
                person_id, project_id
            )

            if existing_subscription:
                # Handle existing subscription based on status
                if existing_subscription.get("status") == "inactive":
                    # Reactivate declined subscription
                    subscription_update = SubscriptionUpdate(
                        status="pending", notes=notes or "Reactivated subscription"
                    )
                    updated_subscription = await db_service.update_subscription(
                        existing_subscription["id"], subscription_update
                    )

                    return {
                        "message": "Subscription reactivated successfully",
                        "subscription": updated_subscription,
                        "person_created": False,
                        "reactivated": True,
                        "version": "v2",
                    }
                else:
                    # Subscription already exists and is active/pending
                    return {
                        "message": "Subscription already exists",
                        "subscription": existing_subscription,
                        "person_created": False,
                        "already_exists": True,
                        "version": "v2",
                    }
        else:
            # Create new person with generated password
            temporary_password = email_service.generate_temporary_password()

            # Hash the temporary password
            hashed_password = PasswordHasher.hash_password(temporary_password)

            # Add password to person data
            person_data["password_hash"] = hashed_password

            # Validate person data
            person_create = PersonCreate(**person_data)

            try:
                created_person = await db_service.create_person(person_create)
                person_id = created_person.id
                person_created = True
                logger.info(f"Created new person: {person_id}")
            except Exception as create_error:
                logger.error(f"Error creating person: {create_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create person: {str(create_error)}",
                )

        # Create subscription
        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status="pending",  # Requires administrator approval before activation
            notes=notes,
        )

        # Create the subscription
        created_subscription = await db_service.create_subscription(subscription_create)

        # Send welcome email with temporary password if new user
        email_sent = False
        email_error = None

        if person_created and temporary_password:
            try:
                email_response = await email_service.send_welcome_email(
                    email=person_data["email"],
                    first_name=person_data["firstName"],
                    last_name=person_data["lastName"],
                    project_name=project.get("name", "Proyecto"),
                    temporary_password=temporary_password,
                )
                email_sent = email_response.success
                if not email_sent:
                    email_error = email_response.message
                    logger.warning(
                        f"Failed to send welcome email: {email_response.message}"
                    )
            except Exception as e:
                email_error = str(e)
                logger.error(f"Error sending welcome email: {str(e)}")

        # Prepare response message
        if person_created:
            if email_sent:
                message = "¡Suscripción creada exitosamente! Se ha enviado un email de bienvenida con tus credenciales de acceso."
            else:
                message = f"Suscripción creada exitosamente. Sin embargo, no se pudo enviar el email de bienvenida: {email_error}"
        else:
            message = "Suscripción creada exitosamente para usuario existente."

        return {
            "message": message,
            "subscription": created_subscription,
            "person_created": person_created,
            "email_sent": email_sent,
            "temporary_password_generated": temporary_password is not None,
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


@auth_router.post("/user/login")
async def user_login(login_request: LoginRequest, request: Request):
    """
    Authenticate regular user (non-admin) and return JWT tokens.

    This endpoint is specifically for regular users who have accounts
    created through the subscription process.
    """
    try:
        logger.log_api_request("POST", "/auth/user/login")

        # Check if user exists and has a password set
        try:
            person = await db_service.get_person_by_email(login_request.email)
            if not person:
                logger.log_api_response("POST", "/auth/user/login", 404)
                return {
                    "success": False,
                    "message": "No se encontró una cuenta con este email. ¿Necesitas crear una cuenta?",
                    "error_code": "USER_NOT_FOUND",
                }

            # Check if person has a password set
            if not hasattr(person, "password_hash") or not person.password_hash:
                logger.log_api_response("POST", "/auth/user/login", 400)
                return {
                    "success": False,
                    "message": "Tu cuenta no tiene una contraseña configurada. Contacta al administrador.",
                    "error_code": "NO_PASSWORD_SET",
                }

        except Exception as e:
            logger.error(f"Error checking user existence: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verificando usuario",
            )

        # Verify password
        if not PasswordHasher.verify_password(
            login_request.password, person.password_hash
        ):
            logger.log_api_response("POST", "/auth/user/login", 401)
            return {
                "success": False,
                "message": "Contraseña incorrecta. Por favor verifica tus credenciales.",
                "error_code": "INVALID_PASSWORD",
            }

        # Generate JWT token for user
        token_data = {
            "sub": person.id,
            "email": person.email,
            "user_type": "user",
            "first_name": person.first_name,
            "last_name": person.last_name,
        }

        access_token = JWTManager.create_access_token(person.id, token_data)

        logger.log_api_response("POST", "/auth/user/login", 200)

        return {
            "success": True,
            "token": access_token,
            "user": {
                "id": person.id,
                "firstName": person.first_name,
                "lastName": person.last_name,
                "email": person.email,
            },
            "message": "Inicio de sesión exitoso",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User login failed",
            operation="user_login",
            email=login_request.email,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en el servicio de autenticación",
        )


@auth_router.get("/user/subscriptions")
async def get_user_subscriptions(request: Request):
    """
    Get subscriptions for the authenticated user.
    """
    try:
        logger.log_api_request("GET", "/auth/user/subscriptions")

        # Extract user from JWT token
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación requerido",
            )

        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        current_user = await auth_middleware.get_current_user(credentials)

        # Get user's subscriptions
        user_subscriptions = await db_service.get_subscriptions_by_person(
            current_user["sub"]
        )

        # Enhance subscriptions with project details
        enhanced_subscriptions = []
        for subscription in user_subscriptions:
            try:
                project = await db_service.get_project_by_id(
                    subscription.get("projectId")
                )
                enhanced_subscription = {
                    "id": subscription.get("id"),
                    "projectId": subscription.get("projectId"),
                    "projectName": (
                        project.get("name", "Proyecto Desconocido")
                        if project
                        else "Proyecto Desconocido"
                    ),
                    "status": subscription.get("status"),
                    "subscribedAt": subscription.get("createdAt"),
                    "notes": subscription.get("notes", ""),
                }
                enhanced_subscriptions.append(enhanced_subscription)
            except Exception as e:
                logger.warning(
                    f"Error enhancing subscription {subscription.get('id')}: {str(e)}"
                )
                # Add subscription without enhancement
                enhanced_subscriptions.append(
                    {
                        "id": subscription.get("id"),
                        "projectId": subscription.get("projectId"),
                        "projectName": "Proyecto Desconocido",
                        "status": subscription.get("status"),
                        "subscribedAt": subscription.get("createdAt"),
                        "notes": subscription.get("notes", ""),
                    }
                )

        logger.log_api_response("GET", "/auth/user/subscriptions", 200)

        return {"subscriptions": enhanced_subscriptions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get user subscriptions",
            operation="get_user_subscriptions",
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo suscripciones del usuario",
        )


@auth_router.post("/user/subscribe")
async def user_subscribe_to_project(request: Request, subscription_data: dict):
    """
    Subscribe authenticated user to a project.
    """
    try:
        logger.log_api_request("POST", "/auth/user/subscribe")

        # Extract user from JWT token
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación requerido",
            )

        token = auth_header.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        current_user = await auth_middleware.get_current_user(credentials)

        project_id = subscription_data.get("projectId")
        notes = subscription_data.get("notes", "")

        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="projectId es requerido"
            )

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado"
            )

        # Check if already subscribed
        existing_subscription = await db_service.get_existing_subscription(
            current_user["sub"], project_id
        )

        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya estás suscrito a este proyecto",
            )

        # Create subscription
        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=current_user["sub"],
            status="pending",
            notes=notes,
        )

        created_subscription = await db_service.create_subscription(subscription_create)

        logger.log_api_response("POST", "/auth/user/subscribe", 201)

        return {
            "success": True,
            "subscription": created_subscription,
            "message": "Suscripción creada exitosamente",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create user subscription",
            operation="user_subscribe_to_project",
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando suscripción",
        )


@auth_router.get("/me")
async def get_current_user_info(request: Request):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    try:
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
                    and hasattr(current_user.last_login_at, "isoformat")
                    else (
                        str(current_user.last_login_at)
                        if current_user.last_login_at
                        else None
                    )
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


@auth_router.post("/people/{person_id}/unlock", response_model=AdminUnlockResponse)
async def unlock_account(
    person_id: str,
    unlock_request: AdminUnlockRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    Unlock a locked user account (admin only).

    This endpoint allows administrators to unlock user accounts that have been
    locked due to failed login attempts or other security measures.
    """
    try:
        logger.log_api_request(
            "POST",
            f"/auth/people/{person_id}/unlock",
            {
                "person_id": person_id,
                "admin_user": current_user.id if current_user else None,
            },
        )

        # Check if user exists
        person = await db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PERSON_NOT_FOUND",
                    "message": "Person not found",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_unlock_{int(datetime.now().timestamp())}",
                },
            )

        # Check if account is actually locked
        lockout_info = await db_service.get_account_lockout(person_id)
        if (
            not lockout_info
            or not lockout_info.locked_until
            or lockout_info.locked_until <= datetime.utcnow()
        ):
            return AdminUnlockResponse(
                success=True,
                message="Account is not locked",
                unlocked_at=datetime.now().isoformat(),
            )

        # Clear the account lockout
        await db_service.clear_account_lockout(person_id)

        # Reset failed login attempts
        update_data = PersonUpdate()
        update_data.failed_login_attempts = 0
        update_data.account_locked_until = None

        await db_service.update_person(person_id, update_data)

        # Log security event
        from ..models.auth import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.ADMIN_ACCOUNT_UNLOCK,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.MEDIUM,
            person_id=person_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={
                "target_user_id": person_id,
                "reason": unlock_request.reason,
                "admin_user_id": current_user.id if current_user else None,
                "previous_failed_attempts": getattr(person, "failed_login_attempts", 0),
            },
        )

        await db_service.log_security_event(security_event)

        logger.log_api_response("POST", f"/auth/people/{person_id}/unlock", 200)

        return AdminUnlockResponse(
            success=True,
            message=f"Account unlocked successfully. Reason: {unlock_request.reason}",
            unlocked_at=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to unlock account",
            operation="unlock_account",
            person_id=person_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise handle_database_error("unlocking account", e)


@v2_router.post("/people/{person_id}/unlock", response_model=AdminUnlockResponse)
async def unlock_account_v2(
    person_id: str,
    unlock_request: AdminUnlockRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    Unlock a locked user account (admin only) - V2 endpoint.
    """
    # Reuse the same logic as the auth endpoint
    return await unlock_account(person_id, unlock_request, request, current_user)


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
        active_projects = [p for p in projects if p.get("status") == "active"]

        # Count subscriptions by status
        active_subscriptions = [s for s in subscriptions if s.get("status") == "active"]
        pending_subscriptions = [s for s in subscriptions if s.get("status") == "pending"]
        # Current subscriptions = active + pending (excludes inactive)
        current_subscriptions = active_subscriptions + pending_subscriptions

        # Get recent activity (last 10 subscriptions)
        recent_subscriptions = sorted(
            subscriptions, key=lambda x: x.get("createdAt", ""), reverse=True
        )[:10]

        # Create dashboard data
        dashboard_data = {
            "totalProjects": len(projects),
            "activeProjects": len(active_projects),
            # Show current subscriptions (active + pending) instead of all including inactive
            "totalSubscriptions": len(current_subscriptions),
            "activeSubscriptions": len(active_subscriptions),
            "pendingSubscriptions": len(pending_subscriptions),
            # For transparency, also include total count including inactive
            "totalSubscriptionsEverCreated": len(subscriptions),
            "recentActivity": recent_subscriptions,
            "statistics": {
                "projectsCreatedThisMonth": len(
                    [
                        p
                        for p in projects
                        if p.get("createdAt", "").startswith("2025-08")
                    ]
                ),
                # Count current subscriptions from this month (active + pending)
                "subscriptionsThisMonth": len(
                    [
                        s
                        for s in current_subscriptions
                        if s.get("createdAt", "").startswith("2025-08")
                    ]
                ),
                # Calculate average based on current subscriptions
                "averageSubscriptionsPerProject": len(current_subscriptions)
                / max(len(projects), 1),
            },
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

        # Get all people from database with error handling
        try:
            people = await db_service.list_people(limit=1000)
        except Exception as db_error:
            logger.error(f"Database error in list_people: {db_error}")
            # Fallback: try to get people directly from DynamoDB
            try:
                response = db_service.table.scan(Limit=1000)
                people = []
                for item in response.get("Items", []):
                    # Create a simple dict instead of Person object to avoid validation
                    people.append(item)
            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {fallback_error}")
                raise handle_database_error("getting admin people", db_error)

        # Convert to admin-friendly format with additional fields
        admin_people = []
        for person in people:
            # Handle both Person objects and dict formats safely
            try:
                # Check if it's a Person object or dict
                if hasattr(person, "__dict__"):
                    # Person object
                    admin_person = {
                        "id": getattr(person, "id", None),
                        "email": getattr(person, "email", None),
                        "firstName": getattr(person, "first_name", None),
                        "lastName": getattr(person, "last_name", None),
                        "phone": getattr(person, "phone", None),
                        "dateOfBirth": getattr(person, "date_of_birth", None),
                        "address": getattr(person, "address", None),
                        "isAdmin": getattr(person, "is_admin", False),
                        "createdAt": getattr(person, "created_at", None),
                        "updatedAt": getattr(person, "updated_at", None),
                        # Add security fields for admin view
                        "isActive": getattr(person, "is_active", True),
                        "requirePasswordChange": getattr(
                            person, "require_password_change", False
                        ),
                        "lastLoginAt": getattr(person, "last_login_at", None),
                        "failedLoginAttempts": getattr(
                            person, "failed_login_attempts", 0
                        ),
                    }
                else:
                    # Dict format (from fallback)
                    admin_person = {
                        "id": person.get("id"),
                        "email": person.get("email"),
                        "firstName": person.get("firstName"),
                        "lastName": person.get("lastName"),
                        "phone": person.get("phone"),
                        "dateOfBirth": person.get("dateOfBirth"),
                        "address": person.get("address"),
                        "isAdmin": person.get("isAdmin", False),
                        "createdAt": person.get("createdAt"),
                        "updatedAt": person.get("updatedAt"),
                        # Add security fields for admin view
                        "isActive": person.get("isActive", True),
                        "requirePasswordChange": person.get(
                            "requirePasswordChange", False
                        ),
                        "lastLoginAt": person.get("lastLoginAt"),
                        "failedLoginAttempts": person.get("failedLoginAttempts", 0),
                    }
                admin_people.append(admin_person)
            except Exception as person_error:
                logger.warning(
                    f"Error processing person {getattr(person, 'id', person.get('id', 'unknown'))}: {person_error}"
                )
                continue

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
            project_subscriptions = [
                s for s in subscriptions if s.get("projectId") == project.get("id")
            ]
            
            # Count subscriptions by status
            active_subs = [s for s in project_subscriptions if s.get("status") == "active"]
            pending_subs = [s for s in project_subscriptions if s.get("status") == "pending"]
            
            enhanced_project = {
                **project,
                # subscriptionCount should reflect active + pending (not inactive)
                "subscriptionCount": len(active_subs) + len(pending_subs),
                "activeSubscriptions": len(active_subs),
                "pendingSubscriptions": len(pending_subs),
                # For transparency, also include total count including inactive
                "totalSubscriptionsEverCreated": len(project_subscriptions),
                "availableSlots": (
                    max(
                        0,
                        project.get("maxParticipants", 0) - len(active_subs),
                    )
                    if project.get("maxParticipants")
                    else None
                ),
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


@v2_router.get("/projects/{project_id}")
async def get_project_v2(project_id: str):
    """Get a specific project by ID (v2)."""
    try:
        logger.log_api_request("GET", f"/v2/projects/{project_id}")

        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        response = create_v2_response(project)
        logger.log_api_response("GET", f"/v2/projects/{project_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get project",
            operation="get_project_v2",
            project_id=project_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting project", e)


@v2_router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project_v2(
    project_data: dict, current_user: dict = Depends(get_current_user)
):
    """Create a new project (v2)."""
    try:
        logger.log_api_request("POST", "/v2/projects")

        # Validate required fields
        if not project_data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name is required",
            )

        # Prepare project data with defaults for required fields
        from datetime import datetime, timedelta

        # Set default values for missing required fields
        today = datetime.now().date()
        project_create_data = {
            "name": project_data["name"],
            "description": project_data.get("description", ""),
            "startDate": project_data.get("startDate", today.isoformat()),
            "endDate": project_data.get(
                "endDate", (today + timedelta(days=365)).isoformat()
            ),
            "maxParticipants": project_data.get("maxParticipants", 100),
            "status": project_data.get("status", "active"),
        }

        # Convert dict to ProjectCreate object
        project_create_obj = ProjectCreate(**project_create_data)

        # Create project with current user as creator
        created_by = current_user.get("id") or current_user.get("sub")
        project = await db_service.create_project(project_create_obj, created_by)

        response = create_v2_response(project)
        logger.log_api_response("POST", "/v2/projects", 201)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create project",
            operation="create_project_v2",
            error_type=type(e).__name__,
        )
        raise handle_database_error("creating project", e)


@v2_router.put("/projects/{project_id}")
async def update_project_v2(
    project_id: str, project_data: dict, current_user: dict = Depends(get_current_user)
):
    """Update a project (v2)."""
    try:
        logger.log_api_request("PUT", f"/v2/projects/{project_id}")

        # Check if project exists
        existing_project = await db_service.get_project_by_id(project_id)
        if not existing_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Convert dict to ProjectUpdate object

        project_update_obj = ProjectUpdate(**project_data)

        # Update project
        updated_project = await db_service.update_project(
            project_id, project_update_obj
        )
        if not updated_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        response = create_v2_response(updated_project)
        logger.log_api_response("PUT", f"/v2/projects/{project_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update project",
            operation="update_project_v2",
            project_id=project_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("updating project", e)


@v2_router.delete("/projects/{project_id}")
async def delete_project_v2(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a project (v2)."""
    try:
        logger.log_api_request("DELETE", f"/v2/projects/{project_id}")

        # Check if project exists
        existing_project = await db_service.get_project_by_id(project_id)
        if not existing_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Delete project
        success = await db_service.delete_project(project_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project",
            )

        response = create_v2_response({"deleted": True, "project_id": project_id})
        logger.log_api_response("DELETE", f"/v2/projects/{project_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete project",
            operation="delete_project_v2",
            project_id=project_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("deleting project", e)


@v2_router.get("/admin/subscriptions")
async def get_admin_subscriptions():
    """Get all subscriptions for admin management with enhanced details (v2)."""
    try:
        logger.log_api_request("GET", "/v2/admin/subscriptions")

        # Get all subscriptions
        subscriptions = await db_service.get_all_subscriptions()

        # Get people and projects for enhanced details
        people = await db_service.list_people(limit=1000)
        projects = await db_service.get_all_projects()

        # Create lookup dictionaries safely
        people_dict = {}
        for p in people:
            person_id = getattr(p, "id", None)
            if person_id:
                people_dict[person_id] = p

        projects_dict = {p.get("id"): p for p in projects if p.get("id")}

        # Enhance subscriptions with person and project details
        enhanced_subscriptions = []
        for subscription in subscriptions:
            try:
                person = people_dict.get(subscription.get("personId"))
                project = projects_dict.get(subscription.get("projectId"))

                enhanced_subscription = {
                    **subscription,
                    "person": (
                        {
                            "id": getattr(person, "id", None),
                            "email": getattr(person, "email", None),
                            "firstName": getattr(person, "first_name", None),
                            "lastName": getattr(person, "last_name", None),
                        }
                        if person
                        else None
                    ),
                    "project": (
                        {
                            "id": project.get("id"),
                            "name": project.get("name"),
                            "status": project.get("status"),
                        }
                        if project
                        else None
                    ),
                }
                enhanced_subscriptions.append(enhanced_subscription)
            except Exception as sub_error:
                logger.warning(
                    f"Error processing subscription {subscription.get('id', 'unknown')}: {sub_error}"
                )
                # Add subscription without enhancement if there's an error
                enhanced_subscriptions.append(subscription)

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


@v2_router.get("/admin/registrations")
async def get_admin_registrations():
    """Get all registrations for admin management (v2) - alias for subscriptions."""
    try:
        logger.log_api_request("GET", "/v2/admin/registrations")

        # Registrations are essentially subscriptions in this system
        # This endpoint provides the same data as subscriptions but with different naming
        subscriptions = await db_service.get_all_subscriptions()

        # Transform subscriptions to registrations format
        registrations = []
        for subscription in subscriptions:
            registration = {
                "id": subscription.get("id"),
                "personId": subscription.get("personId"),
                "projectId": subscription.get("projectId"),
                "status": subscription.get("status"),
                "registrationDate": subscription.get("createdAt"),
                "notes": subscription.get("notes"),
                "createdAt": subscription.get("createdAt"),
                "updatedAt": subscription.get("updatedAt"),
            }
            registrations.append(registration)

        response = create_v2_response(registrations)
        logger.log_api_response("GET", "/v2/admin/registrations", 200)
        return response

    except Exception as e:
        logger.error(
            "Failed to get admin registrations",
            operation="get_admin_registrations",
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting admin registrations", e)


# Router registration moved to end of file after all endpoints are defined


# ==================== EVENTS ENDPOINTS ====================


@v1_router.get("/events")
async def get_events_v1():
    """Get all events (v1 - legacy version)."""
    try:
        logger.log_api_request("GET", "/v1/events")
        # For now, return projects as events for backward compatibility
        projects = await db_service.get_all_projects()

        # Transform projects to events format for legacy compatibility
        events = []
        for project in projects:
            event = {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description"),
                "startDate": project.get("startDate"),
                "endDate": project.get("endDate"),
                "location": project.get("location"),
                "status": project.get("status"),
                "maxParticipants": project.get("maxParticipants"),
                "createdAt": project.get("createdAt"),
                "updatedAt": project.get("updatedAt"),
            }
            events.append(event)

        response = create_v1_response(events)
        logger.log_api_response("GET", "/v1/events", 200)
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve events",
            operation="get_events_v1",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving events", e)


@v2_router.get("/events")
async def get_events_v2():
    """Get all events (v2 - enhanced version)."""
    try:
        logger.log_api_request("GET", "/v2/events")
        # For now, return projects as events for backward compatibility
        projects = await db_service.get_all_projects()

        # Transform projects to events format with enhanced data
        events = []
        for project in projects:
            event = {
                "id": project.get("id"),
                "name": project.get("name"),
                "description": project.get("description"),
                "startDate": project.get("startDate"),
                "endDate": project.get("endDate"),
                "location": project.get("location"),
                "status": project.get("status"),
                "maxParticipants": project.get("maxParticipants"),
                "createdAt": project.get("createdAt"),
                "updatedAt": project.get("updatedAt"),
                "type": "project",  # Enhanced field
                "category": project.get("category", "workshop"),  # Enhanced field
            }
            events.append(event)

        response = create_v2_response(events, metadata={"total_count": len(events)})
        logger.log_api_response(
            "GET", "/v2/events", 200, additional_context={"count": len(events)}
        )
        return response
    except Exception as e:
        logger.error(
            "Failed to retrieve events",
            operation="get_events_v2",
            error_type=type(e).__name__,
        )
        raise handle_database_error("retrieving events", e)


# Legacy endpoints (unversioned) - redirect to v1 for compatibility
@app.get("/subscriptions")
async def get_subscriptions_legacy():
    """Legacy endpoint - redirects to v1."""
    return await get_subscriptions_v1()


@app.get("/projects")
async def get_projects_legacy():
    """Legacy endpoint - redirects to v2 for better functionality."""
    return await get_projects_v2()


@app.get("/events")
async def get_events_legacy():
    """Legacy events endpoint - redirects to v1."""
    return await get_events_v1()


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
            people = await db_service.list_people(limit=100)
            return {
                "people": [person.dict() for person in people],
                "version": "v2",
                "count": len(people),
            }
    except Exception as e:
        raise handle_database_error("getting people (v2)", e)


@v2_router.post("/people", status_code=status.HTTP_201_CREATED)
async def create_person_v2(person_data: PersonCreate):
    """Create a new person (v2)."""
    try:
        logger.log_api_request("POST", "/v2/people")

        # Create the person
        created_person = await db_service.create_person(person_data)

        # Convert to response format
        person_response_data = {
            "id": created_person.id,
            "email": created_person.email,
            "firstName": created_person.first_name,
            "lastName": created_person.last_name,
            "phone": created_person.phone or "",
            "dateOfBirth": (
                created_person.date_of_birth.isoformat()
                if created_person.date_of_birth
                and hasattr(created_person.date_of_birth, "isoformat")
                else (
                    str(created_person.date_of_birth)
                    if created_person.date_of_birth
                    else ""
                )
            ),
            "address": {
                "country": (
                    getattr(created_person.address, "country", "")
                    if created_person.address
                    else ""
                ),
                "state": (
                    getattr(created_person.address, "state", "")
                    if created_person.address
                    else ""
                ),
                "city": (
                    getattr(created_person.address, "city", "")
                    if created_person.address
                    else ""
                ),
                "street": (
                    getattr(created_person.address, "street", "")
                    if created_person.address
                    else ""
                ),
                "postalCode": (
                    getattr(created_person.address, "postal_code", "")
                    if created_person.address
                    else ""
                ),
            },
            "isAdmin": created_person.is_admin,
            "createdAt": (
                created_person.created_at.isoformat()
                if created_person.created_at
                and hasattr(created_person.created_at, "isoformat")
                else str(created_person.created_at) if created_person.created_at else ""
            ),
            "updatedAt": (
                created_person.updated_at.isoformat()
                if created_person.updated_at
                and hasattr(created_person.updated_at, "isoformat")
                else str(created_person.updated_at) if created_person.updated_at else ""
            ),
            "isActive": getattr(created_person, "is_active", True),
            "requirePasswordChange": getattr(
                created_person, "require_password_change", False
            ),
            "lastLoginAt": (
                created_person.last_login_at.isoformat()
                if getattr(created_person, "last_login_at", None)
                and hasattr(created_person.last_login_at, "isoformat")
                else (
                    str(created_person.last_login_at)
                    if getattr(created_person, "last_login_at", None)
                    else None
                )
            ),
            "failedLoginAttempts": getattr(created_person, "failed_login_attempts", 0),
        }

        response = create_v2_response(person_response_data)
        logger.log_api_response("POST", "/v2/people", 201)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create person",
            operation="create_person_v2",
            error_type=type(e).__name__,
            error_message=str(e),
            error_details=repr(e),
        )
        # Log the full traceback for debugging
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise handle_database_error("creating person", e)


@v2_router.put("/people/{person_id}/admin")
async def update_admin_status(person_id: str, admin_data: dict):
    """Update admin status for a person (admin only)."""
    try:
        # TODO: Add proper authentication middleware to verify admin user
        # For now, we'll implement basic validation

        is_admin = admin_data.get("isAdmin", False)

        # Get the person to update
        person = await db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Convert dict to PersonUpdate object
        update_data = {"isAdmin": is_admin}
        person_update_obj = PersonUpdate(**update_data)

        # Update admin status
        updated_person = await db_service.update_person(person_id, person_update_obj)

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


@v2_router.get("/people/{person_id}")
async def get_person_v2(person_id: str):
    """Get a specific person by ID (v2)."""
    try:
        logger.log_api_request("GET", f"/v2/people/{person_id}")

        person = await db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Convert to response format
        person_data = {
            "id": person.id,
            "email": person.email,
            "firstName": person.first_name,
            "lastName": person.last_name,
            "phone": person.phone or "",
            "dateOfBirth": (
                person.date_of_birth.isoformat()
                if person.date_of_birth and hasattr(person.date_of_birth, "isoformat")
                else str(person.date_of_birth) if person.date_of_birth else ""
            ),
            "address": {
                "country": (
                    getattr(person.address, "country", "") if person.address else ""
                ),
                "state": getattr(person.address, "state", "") if person.address else "",
                "city": getattr(person.address, "city", "") if person.address else "",
                "street": (
                    getattr(person.address, "street", "") if person.address else ""
                ),
                "postalCode": (
                    getattr(person.address, "postal_code", "") if person.address else ""
                ),
            },
            "isAdmin": person.is_admin,
            "createdAt": (
                person.created_at.isoformat()
                if person.created_at and hasattr(person.created_at, "isoformat")
                else str(person.created_at) if person.created_at else ""
            ),
            "updatedAt": (
                person.updated_at.isoformat()
                if person.updated_at and hasattr(person.updated_at, "isoformat")
                else str(person.updated_at) if person.updated_at else ""
            ),
            "isActive": person.is_active,
            "requirePasswordChange": person.require_password_change,
            "lastLoginAt": (
                person.last_login_at.isoformat()
                if person.last_login_at and hasattr(person.last_login_at, "isoformat")
                else str(person.last_login_at) if person.last_login_at else None
            ),
            "failedLoginAttempts": person.failed_login_attempts or 0,
        }

        response = create_v2_response(person_data)
        logger.log_api_response("GET", f"/v2/people/{person_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get person",
            operation="get_person_v2",
            person_id=person_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting person", e)


@v2_router.put("/people/{person_id}")
async def update_person_v2(person_id: str, person_update: dict):
    """Update a person (v2)."""
    try:
        logger.log_api_request("PUT", f"/v2/people/{person_id}")

        # Check if person exists
        existing_person = await db_service.get_person(person_id)
        if not existing_person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Convert dict to PersonUpdate object
        logger.info(f"Creating PersonUpdate object with data: {person_update}")
        person_update_obj = PersonUpdate(**person_update)
        logger.info(f"PersonUpdate object created successfully")

        # Update the person
        logger.info(f"Calling db_service.update_person")
        updated_person = await db_service.update_person(person_id, person_update_obj)
        logger.info(f"Person updated successfully, creating response")

        # Convert to response format
        person_data = {
            "id": updated_person.id,
            "email": updated_person.email,
            "firstName": updated_person.first_name,
            "lastName": updated_person.last_name,
            "phone": updated_person.phone or "",
            "dateOfBirth": (
                updated_person.date_of_birth.isoformat()
                if updated_person.date_of_birth
                and hasattr(updated_person.date_of_birth, "isoformat")
                else (
                    str(updated_person.date_of_birth)
                    if updated_person.date_of_birth
                    else ""
                )
            ),
            "address": {
                "country": (
                    getattr(updated_person.address, "country", "")
                    if updated_person.address
                    else ""
                ),
                "state": (
                    getattr(updated_person.address, "state", "")
                    if updated_person.address
                    else ""
                ),
                "city": (
                    getattr(updated_person.address, "city", "")
                    if updated_person.address
                    else ""
                ),
                "street": (
                    getattr(updated_person.address, "street", "")
                    if updated_person.address
                    else ""
                ),
                "postalCode": (
                    getattr(updated_person.address, "postal_code", "")
                    if updated_person.address
                    else ""
                ),
            },
            "isAdmin": updated_person.is_admin,
            "createdAt": (
                updated_person.created_at.isoformat()
                if updated_person.created_at
                and hasattr(updated_person.created_at, "isoformat")
                else str(updated_person.created_at) if updated_person.created_at else ""
            ),
            "updatedAt": (
                updated_person.updated_at.isoformat()
                if updated_person.updated_at
                and hasattr(updated_person.updated_at, "isoformat")
                else str(updated_person.updated_at) if updated_person.updated_at else ""
            ),
            "isActive": getattr(updated_person, "is_active", True),
            "requirePasswordChange": getattr(
                updated_person, "require_password_change", False
            ),
            "lastLoginAt": (
                updated_person.last_login_at.isoformat()
                if getattr(updated_person, "last_login_at", None)
                and hasattr(updated_person.last_login_at, "isoformat")
                else (
                    str(updated_person.last_login_at)
                    if getattr(updated_person, "last_login_at", None)
                    else None
                )
            ),
            "failedLoginAttempts": getattr(updated_person, "failed_login_attempts", 0),
        }

        response = create_v2_response(person_data)
        logger.log_api_response("PUT", f"/v2/people/{person_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update person",
            operation="update_person_v2",
            person_id=person_id,
            error_type=type(e).__name__,
            error_message=str(e),
            error_details=repr(e),
        )
        # Log the full traceback for debugging
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise handle_database_error("updating person", e)


@v2_router.delete("/people/{person_id}")
async def delete_person_v2(person_id: str):
    """Delete a person (v2)."""
    try:
        logger.log_api_request("DELETE", f"/v2/people/{person_id}")

        # Check if person exists
        existing_person = await db_service.get_person(person_id)
        if not existing_person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Delete the person
        await db_service.delete_person(person_id)

        logger.log_api_response("DELETE", f"/v2/people/{person_id}", 204)
        return {"message": "Person deleted successfully", "version": "v2"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete person",
            operation="delete_person_v2",
            person_id=person_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("deleting person", e)


# ==================== V2 PROJECT SUBSCRIPTION MANAGEMENT ====================


@v2_router.get("/projects/{project_id}/subscribers")
async def get_project_subscribers_v2(project_id: str):
    """Get all subscribers for a specific project (v2)."""
    try:
        logger.log_api_request("GET", f"/v2/projects/{project_id}/subscribers")

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Get all subscriptions for this project
        all_subscriptions = await db_service.get_all_subscriptions()
        project_subscriptions = [
            sub for sub in all_subscriptions if sub.get("projectId") == project_id
        ]

        # Get people details for each subscription
        people = await db_service.list_people(limit=1000)
        people_dict = {}
        for p in people:
            person_id = getattr(p, "id", None)
            if person_id:
                people_dict[person_id] = {
                    "id": person_id,
                    "firstName": getattr(p, "first_name", ""),
                    "lastName": getattr(p, "last_name", ""),
                    "email": getattr(p, "email", ""),
                }

        # Enhance subscriptions with person details
        enhanced_subscriptions = []
        for subscription in project_subscriptions:
            person_id = subscription.get("personId")
            person_info = people_dict.get(
                person_id,
                {
                    "id": person_id,
                    "firstName": "Unknown",
                    "lastName": "User",
                    "email": "unknown@example.com",
                },
            )

            enhanced_subscription = {
                "id": subscription.get("id"),
                "personId": person_id,
                "projectId": project_id,
                "status": subscription.get("status", "active"),
                "subscribedAt": subscription.get("createdAt"),
                "subscribedBy": subscription.get("subscribedBy"),
                "notes": subscription.get("notes", ""),
                "person": person_info,
            }
            enhanced_subscriptions.append(enhanced_subscription)

        # Calculate metadata
        total_count = len(enhanced_subscriptions)
        active_count = len(
            [s for s in enhanced_subscriptions if s["status"] == "active"]
        )
        pending_count = len(
            [s for s in enhanced_subscriptions if s["status"] == "pending"]
        )

        response_data = {
            "subscribers": enhanced_subscriptions,
            "metadata": {
                "totalCount": total_count,
                "activeCount": active_count,
                "pendingCount": pending_count,
                "projectId": project_id,
                "projectName": project.get("name", "Unknown Project"),
            },
        }

        response = create_v2_response(response_data)
        logger.log_api_response("GET", f"/v2/projects/{project_id}/subscribers", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get project subscribers",
            operation="get_project_subscribers_v2",
            project_id=project_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("getting project subscribers", e)


@v2_router.post("/projects/{project_id}/subscribers")
async def subscribe_person_to_project_v2(project_id: str, subscription_data: dict):
    """Subscribe a person to a project (v2)."""
    try:
        logger.log_api_request("POST", f"/v2/projects/{project_id}/subscribers")

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Extract and validate required fields
        person_id = subscription_data.get("personId")
        if not person_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="personId is required"
            )

        # Verify person exists
        person = await db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Check if subscription already exists
        all_subscriptions = await db_service.get_all_subscriptions()
        existing_subscription = next(
            (
                sub
                for sub in all_subscriptions
                if sub.get("personId") == person_id
                and sub.get("projectId") == project_id
            ),
            None,
        )

        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Person is already subscribed to this project",
            )

        # Create subscription
        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status=subscription_data.get("status", "active"),
            notes=subscription_data.get("notes", ""),
            subscribedBy=subscription_data.get("subscribedBy"),
        )

        created_subscription = await db_service.create_subscription(subscription_create)

        # Enhance response with person details
        response_data = {
            "id": created_subscription.get("id"),
            "personId": person_id,
            "projectId": project_id,
            "status": created_subscription.get("status"),
            "subscribedAt": created_subscription.get("createdAt"),
            "subscribedBy": created_subscription.get("subscribedBy"),
            "notes": created_subscription.get("notes", ""),
            "person": {
                "id": person.id,
                "firstName": person.first_name,
                "lastName": person.last_name,
                "email": person.email,
            },
        }

        response = create_v2_response(response_data)
        logger.log_api_response("POST", f"/v2/projects/{project_id}/subscribers", 201)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to subscribe person to project",
            operation="subscribe_person_to_project_v2",
            project_id=project_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("subscribing person to project", e)


@v2_router.put("/projects/{project_id}/subscribers/{subscription_id}")
async def update_project_subscription_v2(
    project_id: str, subscription_id: str, update_data: dict
):
    """Update a project subscription (v2)."""
    try:
        logger.log_api_request(
            "PUT", f"/v2/projects/{project_id}/subscribers/{subscription_id}"
        )

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Find the subscription
        all_subscriptions = await db_service.get_all_subscriptions()
        subscription = next(
            (
                sub
                for sub in all_subscriptions
                if sub.get("id") == subscription_id
                and sub.get("projectId") == project_id
            ),
            None,
        )

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        # Store original status for email notification logic
        original_status = subscription.get("status")
        new_status = update_data.get("status")

        # Create update object
        update_fields = {}
        if "status" in update_data:
            update_fields["status"] = update_data["status"]
        if "notes" in update_data:
            update_fields["notes"] = update_data["notes"]

        subscription_update = SubscriptionUpdate(**update_fields)
        updated_subscription = await db_service.update_subscription(
            subscription_id, subscription_update
        )

        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription",
            )

        # Send email notification if status changed to approved or rejected
        if new_status and new_status != original_status:
            try:
                # Get person details for email notification
                person_id = subscription.get("personId")
                if person_id:
                    person = await db_service.get_person(person_id)
                    if person:
                        project_name = project.get("name", "Proyecto")
                        project_description = project.get("description")

                        if new_status == "active":
                            # Send approval email
                            email_response = (
                                await email_service.send_subscription_approved_email(
                                    email=person.email,
                                    first_name=person.first_name,
                                    last_name=person.last_name,
                                    project_name=project_name,
                                    project_description=project_description,
                                )
                            )

                            if email_response.success:
                                logger.info(
                                    f"Subscription approval email sent successfully to {person.email} for project {project_name}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to send subscription approval email to {person.email}: {email_response.message}"
                                )

                        elif new_status == "inactive":
                            # Send rejection email
                            rejection_reason = update_data.get(
                                "notes", "No se proporcionó una razón específica"
                            )
                            email_response = (
                                await email_service.send_subscription_rejected_email(
                                    email=person.email,
                                    first_name=person.first_name,
                                    last_name=person.last_name,
                                    project_name=project_name,
                                    rejection_reason=rejection_reason,
                                )
                            )

                            if email_response.success:
                                logger.info(
                                    f"Subscription rejection email sent successfully to {person.email} for project {project_name}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to send subscription rejection email to {person.email}: {email_response.message}"
                                )

            except Exception as email_error:
                # Log email error but don't fail the subscription update
                logger.error(
                    f"Error sending subscription status email notification: {str(email_error)}",
                    operation="update_project_subscription_v2_email",
                    subscription_id=subscription_id,
                    person_id=person_id,
                    new_status=new_status,
                    error_type=type(email_error).__name__,
                )

        response = create_v2_response(updated_subscription)
        logger.log_api_response(
            "PUT", f"/v2/projects/{project_id}/subscribers/{subscription_id}", 200
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update project subscription",
            operation="update_project_subscription_v2",
            project_id=project_id,
            subscription_id=subscription_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("updating project subscription", e)


@v2_router.delete("/projects/{project_id}/subscribers/{subscription_id}")
async def unsubscribe_person_from_project_v2(project_id: str, subscription_id: str):
    """Remove a person's subscription from a project (v2)."""
    try:
        logger.log_api_request(
            "DELETE", f"/v2/projects/{project_id}/subscribers/{subscription_id}"
        )

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Find the subscription
        all_subscriptions = await db_service.get_all_subscriptions()
        subscription = next(
            (
                sub
                for sub in all_subscriptions
                if sub.get("id") == subscription_id
                and sub.get("projectId") == project_id
            ),
            None,
        )

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        # Delete subscription
        success = await db_service.delete_subscription(subscription_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete subscription",
            )

        response = create_v2_response(
            {
                "message": "Subscription removed successfully",
                "subscriptionId": subscription_id,
                "projectId": project_id,
            }
        )

        logger.log_api_response(
            "DELETE", f"/v2/projects/{project_id}/subscribers/{subscription_id}", 200
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to remove project subscription",
            operation="unsubscribe_person_from_project_v2",
            project_id=project_id,
            subscription_id=subscription_id,
            error_type=type(e).__name__,
        )
        raise handle_database_error("removing project subscription", e)


# ==================== ROUTER REGISTRATION ====================
# Register all routers after all endpoints are defined

app.include_router(v1_router)
app.include_router(v2_router)
app.include_router(auth_router)
