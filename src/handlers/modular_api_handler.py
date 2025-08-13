"""
Modular API Handler - Clean, maintainable replacement for the monolithic versioned_api_handler.
Uses the Service Registry pattern for better separation of concerns and testability.
"""

import json
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status, Request, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from ..models.person import PersonCreate, PersonUpdate
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.subscription import SubscriptionCreate, SubscriptionUpdate
from ..models.auth import LoginRequest, LoginResponse
from ..services.service_registry_manager import service_manager
from ..middleware.admin_middleware_v2 import (
    require_admin_access,
    require_super_admin_access,
)
from ..middleware.auth_middleware import get_current_user
from ..utils.logging_config import get_handler_logger

# Configure standardized logging
logger = get_handler_logger("modular_api")

# Create FastAPI app
app = FastAPI(
    title="People Register API - Modular (Service Registry)",
    description="""
    ## People Register API with Service Registry Pattern

    This API uses the Service Registry pattern for clean separation of concerns and maintainability.

    ### Architecture Benefits
    - **Modular Design**: Each domain has its own service
    - **Service Registry**: Centralized service management and dependency injection
    - **Health Monitoring**: Individual service health checks
    - **Testability**: Services can be tested in isolation
    - **Maintainability**: Clear separation of concerns

    ### Available Versions
    - **v1**: Current stable version (legacy endpoints)
    - **v2**: Enhanced version with bug fixes and improvements

    ### Service Registry Features
    - Automatic service discovery and registration
    - Health monitoring for all services
    - Configuration management
    - Dependency injection
    - Error handling and logging
    """,
    version="3.0.0-service-registry",
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


# ==================== HEALTH CHECK ENDPOINTS ====================


@app.get("/health")
async def health_check():
    """Comprehensive health check for the entire system."""
    try:
        health_status = await service_manager.health_check()

        # Add API handler information
        health_status["api_handler"] = {
            "status": "healthy",
            "version": "3.0.0-service-registry",
            "architecture": "modular_service_registry",
            "timestamp": datetime.now().isoformat(),
        }

        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "overall_status": "unhealthy",
            "api_handler": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        }


@app.get("/health/services")
async def services_health():
    """Detailed health check for all registered services."""
    return await service_manager.health_check()


# ==================== V1 ENDPOINTS (Legacy) ====================


# People endpoints
@v1_router.get("/people")
async def get_people_v1():
    """Get all people (v1 - legacy version)."""
    return await service_manager.get_all_people_v1()


@v1_router.get("/people/{person_id}")
async def get_person_v1(person_id: str):
    """Get person by ID (v1 - legacy version)."""
    return await service_manager.get_person_by_id_v1(person_id)


@v1_router.post("/people")
async def create_person_v1(person_data: PersonCreate):
    """Create person (v1 - legacy version)."""
    return await service_manager.create_person_v1(person_data)


@v1_router.put("/people/{person_id}")
async def update_person_v1(person_id: str, person_data: PersonUpdate):
    """Update person (v1 - legacy version)."""
    return await service_manager.update_person_v1(person_id, person_data)


@v1_router.delete("/people/{person_id}")
async def delete_person_v1(person_id: str):
    """Delete person (v1 - legacy version)."""
    return await service_manager.delete_person_v1(person_id)


# Projects endpoints
@v1_router.get("/projects")
async def get_projects_v1():
    """Get all projects (v1 - legacy version)."""
    return await service_manager.get_all_projects_v1()


@v1_router.get("/projects/{project_id}")
async def get_project_v1(project_id: str):
    """Get project by ID (v1 - legacy version)."""
    return await service_manager.get_project_by_id_v1(project_id)


@v1_router.post("/projects")
async def create_project_v1(project_data: ProjectCreate):
    """Create project (v1 - legacy version)."""
    return await service_manager.create_project_v1(project_data)


@v1_router.put("/projects/{project_id}")
async def update_project_v1(project_id: str, project_data: ProjectUpdate):
    """Update project (v1 - legacy version)."""
    return await service_manager.update_project_v1(project_id, project_data)


@v1_router.delete("/projects/{project_id}")
async def delete_project_v1(project_id: str):
    """Delete project (v1 - legacy version)."""
    return await service_manager.delete_project_v1(project_id)


# Subscriptions endpoints
@v1_router.get("/subscriptions")
async def get_subscriptions_v1():
    """Get all subscriptions (v1 - legacy version)."""
    return await service_manager.get_all_subscriptions_v1()


@v1_router.get("/subscriptions/{subscription_id}")
async def get_subscription_v1(subscription_id: str):
    """Get subscription by ID (v1 - legacy version)."""
    return await service_manager.get_subscription_by_id_v1(subscription_id)


@v1_router.post("/public/subscribe")
async def create_subscription_v1(subscription_data: dict):
    """Create subscription (v1 - now redirects to v2 with password generation).

    DEPRECATED: This endpoint is deprecated. Use /v2/public/subscribe instead.
    For backward compatibility, this now uses the v2 implementation with password generation.
    """
    return await service_manager.create_subscription_v1(subscription_data)


@v1_router.get("/projects/{project_id}/subscriptions")
async def get_project_subscriptions_v1(project_id: str):
    """Get subscriptions for a project (v1 - legacy version)."""
    return await service_manager.get_project_subscriptions_v1(project_id)


# ==================== V2 ENDPOINTS (Enhanced) ====================


# People endpoints
@v2_router.get("/people")
async def get_people_v2():
    """Get all people (v2 - enhanced version)."""
    return await service_manager.get_all_people_v2()


@v2_router.get("/people/{person_id}")
async def get_person_v2(person_id: str):
    """Get person by ID (v2 - enhanced version)."""
    return await service_manager.get_person_by_id_v2(person_id)


@v2_router.post("/people")
async def create_person_v2(person_data: PersonCreate):
    """Create person (v2 - enhanced version)."""
    return await service_manager.create_person_v2(person_data)


@v2_router.put("/people/{person_id}")
async def update_person_v2(person_id: str, person_data: PersonUpdate):
    """Update person (v2 - enhanced version)."""
    return await service_manager.update_person_v2(person_id, person_data)


@v2_router.delete("/people/{person_id}")
async def delete_person_v2(person_id: str):
    """Delete person (v2 - enhanced version)."""
    return await service_manager.delete_person_v2(person_id)


# Projects endpoints
@v2_router.get("/projects")
async def get_projects_v2():
    """Get all projects (v2 - enhanced version)."""
    return await service_manager.get_all_projects_v2()


@v2_router.get("/projects/{project_id}")
async def get_project_v2(project_id: str):
    """Get project by ID (v2 - enhanced version)."""
    return await service_manager.get_project_by_id_v2(project_id)


@v2_router.post("/projects")
async def create_project_v2(project_data: ProjectCreate):
    """Create project (v2 - enhanced version)."""
    return await service_manager.create_project_v2(project_data)


@v2_router.put("/projects/{project_id}")
async def update_project_v2(project_id: str, project_data: ProjectUpdate):
    """Update project (v2 - enhanced version)."""
    return await service_manager.update_project_v2(project_id, project_data)


@v2_router.delete("/projects/{project_id}")
async def delete_project_v2(project_id: str):
    """Delete project (v2 - enhanced version)."""
    return await service_manager.delete_project_v2(project_id)


# Subscriptions endpoints
@v2_router.get("/subscriptions")
async def get_subscriptions_v2():
    """Get all subscriptions (v2 - enhanced version)."""
    return await service_manager.get_all_subscriptions_v2()


@v2_router.get("/subscriptions/{subscription_id}")
async def get_subscription_v2(subscription_id: str):
    """Get subscription by ID (v2 - enhanced version)."""
    return await service_manager.get_subscription_by_id_v2(subscription_id)


@v2_router.post("/public/subscribe")
async def create_subscription_v2(subscription_data: dict):
    """Create subscription (v2 - enhanced version with password generation)."""
    return await service_manager.create_subscription_v2(subscription_data)


@v2_router.get("/projects/{project_id}/subscriptions")
async def get_project_subscriptions_v2(project_id: str):
    """Get subscriptions for a project (v2 - enhanced version)."""
    return await service_manager.get_project_subscriptions_v2(project_id)


# ==================== SERVICE REGISTRY ENDPOINTS ====================


@app.get("/registry/services")
async def list_registered_services():
    """List all registered services in the Service Registry."""
    try:
        services_info = {}
        for service_name in service_manager.registry.services.keys():
            service = service_manager.get_service(service_name)
            services_info[service_name] = {
                "name": service.service_name,
                "status": "registered",
                "type": type(service).__name__,
            }

        return {
            "service_registry": {
                "total_services": len(services_info),
                "services": services_info,
                "timestamp": datetime.now().isoformat(),
            }
        }
    except Exception as e:
        logger.error(f"Failed to list services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service registry information",
        )


@app.get("/registry/config")
async def get_service_config():
    """Get current service configuration."""
    try:
        config_info = {
            "database": {
                "region": service_manager.config.database.region,
                "environment": service_manager.config.environment.value,
            },
            "auth": {
                "access_token_expiry_hours": service_manager.config.auth.access_token_expiry_hours,
                "password_policy": {
                    "min_length": service_manager.config.security.password_min_length,
                    "require_special_chars": service_manager.config.security.password_require_special,
                },
            },
            "email": {
                "region": service_manager.config.email.ses_region,
                "from_address": service_manager.config.email.from_email,
            },
            "security": {
                "rate_limit_requests_per_minute": service_manager.config.security.rate_limit_requests_per_minute,
                "rate_limit_requests_per_hour": service_manager.config.security.rate_limit_requests_per_hour,
            },
        }

        return {"configuration": config_info, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration information",
        )


# ==================== AUTH ENDPOINTS ====================


@auth_router.post("/login", response_model=Dict[str, Any])
async def login(login_request: LoginRequest):
    """Authenticate user and return access token."""
    try:
        auth_service = service_manager.get_service("auth")
        success, login_response, error_message = await auth_service.authenticate_user(
            login_request
        )

        if success and login_response:
            return {
                "success": True,
                "data": {
                    "access_token": login_response.access_token,
                    "refresh_token": login_response.refresh_token,
                    "token_type": login_response.token_type,
                    "expires_in": login_response.expires_in,
                    "user": login_response.user.dict() if login_response.user else None,
                },
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message or "Authentication failed",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


# ==================== ROUTER REGISTRATION ====================
# Register all routers after all endpoints are defined

app.include_router(v1_router)
app.include_router(v2_router)
app.include_router(auth_router)

# Log successful initialization
logger.info("Modular API Handler initialized with Service Registry pattern")
logger.info(f"Registered services: {list(service_manager.registry.services.keys())}")
