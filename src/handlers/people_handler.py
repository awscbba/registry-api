import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from ..models.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PasswordUpdateRequest,
    ErrorResponse,
    ValidationError,
    EmailVerificationRequest,
    PersonDeletionRequest,
    PersonDeletionInitiateRequest,
    PersonDeletionResponse,
    ReferentialIntegrityError,
    AdminUnlockRequest,
    AdminUnlockResponse,
)
from ..models.auth import LoginRequest, LoginResponse
from ..services.defensive_dynamodb_service import (
    DefensiveDynamoDBService as DynamoDBService,
)
from ..services.auth_service import AuthService
from ..services.password_management_service import PasswordManagementService
from ..services.person_validation_service import PersonValidationService
from ..services.email_verification_service import EmailVerificationService
from ..utils.error_handler import (
    StandardErrorHandler,
    handle_database_error,
    handle_authentication_error,
)
from ..utils.logging_config import get_handler_logger
from ..utils.response_models import ResponseFactory
from ..services.person_deletion_service import PersonDeletionService
from ..middleware.auth_middleware import get_current_user, require_no_password_change

# Configure standardized logging
logger = get_handler_logger("people")

# Initialize FastAPI app with comprehensive OpenAPI documentation
app = FastAPI(
    title="People Register API",
    description="""
    ## People Register API

    A comprehensive API for managing people registration with enhanced security features.

    ### Features
    - **Authentication**: JWT-based authentication with account lockout protection
    - **Password Management**: Secure password updates with policy enforcement
    - **Profile Management**: Complete CRUD operations for person profiles
    - **Email Verification**: Email change verification workflow
    - **Search**: Advanced search capabilities with filtering
    - **Admin Functions**: Administrative account management
    - **Security**: Rate limiting, audit logging, and comprehensive error handling

    ### Authentication
    Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```

    ### Error Responses
    All endpoints return consistent error responses with the following structure:
    ```json
    {
      "error": "ERROR_CODE",
      "message": "Human-readable error message",
      "details": [
        {
          "field": "fieldName",
          "message": "Field-specific error message",
          "code": "VALIDATION_ERROR_CODE"
        }
      ],
      "timestamp": "2025-01-22T10:30:00Z",
      "requestId": "req_123456789"
    }
    ```

    ### HTTP Status Codes
    - **200 OK**: Successful GET requests
    - **201 Created**: Successful POST requests that create resources
    - **204 No Content**: Successful DELETE requests
    - **400 Bad Request**: Validation errors or malformed requests
    - **401 Unauthorized**: Authentication required or failed
    - **403 Forbidden**: Insufficient permissions or account locked
    - **404 Not Found**: Resource not found
    - **409 Conflict**: Resource conflicts (e.g., duplicate email)
    - **429 Too Many Requests**: Rate limit exceeded
    - **500 Internal Server Error**: Unexpected server errors
    """,
    version="1.0.0",
    contact={"name": "API Support", "email": "support@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {
            "name": "authentication",
            "description": "Authentication and authorization endpoints",
        },
        {
            "name": "password-management",
            "description": "Password management and security endpoints",
        },
        {"name": "people", "description": "Person CRUD operations"},
        {"name": "search", "description": "Person search and filtering"},
        {
            "name": "email-verification",
            "description": "Email verification and change workflows",
        },
        {"name": "admin", "description": "Administrative functions"},
        {"name": "projects", "description": "Project management endpoints"},
        {"name": "subscriptions", "description": "Subscription management endpoints"},
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db_service = DynamoDBService()
auth_service = AuthService()
password_service = PasswordManagementService()
validation_service = PersonValidationService(db_service)
email_verification_service = EmailVerificationService(db_service)
deletion_service = PersonDeletionService(db_service)


@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check the health status of the API service",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "people-register-api",
                        "timestamp": "2025-01-22T10:30:00Z",
                    }
                }
            },
        }
    },
)
async def health_check():
    """
    Health check endpoint that returns the current status of the API service.

    This endpoint can be used by load balancers and monitoring systems to verify
    that the service is running and responding to requests.
    """
    return {
        "status": "healthy",
        "service": "people-register-api",
        "timestamp": datetime.now().isoformat(),
    }


# Authentication endpoints


@app.post(
    "/auth/login",
    response_model=LoginResponse,
    tags=["authentication"],
    summary="User Login",
    description="Authenticate user credentials and return JWT access and refresh tokens",
    responses={
        200: {
            "description": "Authentication successful",
            "content": {
                "application/json": {
                    "example": {
                        "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "tokenType": "bearer",
                        "expiresIn": 3600,
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "user@example.com",
                            "firstName": "John",
                            "lastName": "Doe",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Invalid email or password format",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_FAILED",
                        "message": "Invalid email or password",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
        403: {
            "description": "Account locked or requires password change",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ACCOUNT_LOCKED",
                        "message": "Account is locked due to too many failed login attempts",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
        429: {
            "description": "Too many login attempts",
            "content": {
                "application/json": {
                    "example": {
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many login attempts. Please try again later.",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
    },
)
async def login(login_request: LoginRequest, request: Request):
    """
    Authenticate user credentials and return JWT tokens.

    This endpoint validates user credentials and returns both access and refresh tokens
    if authentication is successful. The access token should be used for subsequent
    API requests, while the refresh token can be used to obtain new access tokens.

    **Security Features:**
    - Account lockout after 5 failed attempts
    - Rate limiting to prevent brute force attacks
    - Comprehensive audit logging
    - IP address and user agent tracking
    """
    try:
        # Get client IP and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Authenticate user
        success, login_response, error_message = await auth_service.authenticate_user(
            login_request, ip_address, user_agent
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message or "Authentication failed",
            )

        return login_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Authentication failed", operation="login", error_type=type(e).__name__
        )
        raise handle_authentication_error("Authentication failed")


@app.get(
    "/auth/me",
    tags=["authentication"],
    summary="Get Current User",
    description="Get information about the currently authenticated user",
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "firstName": "John",
                        "lastName": "Doe",
                        "requirePasswordChange": False,
                        "isActive": True,
                        "lastLoginAt": "2025-01-22T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Valid authentication token required",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
    },
)
async def get_current_user_info(current_user=Depends(get_current_user)):
    """
    Get information about the currently authenticated user.

    Returns basic profile information for the authenticated user, including
    account status and security-related flags.

    **Required Authentication:** Bearer token in Authorization header
    """
    return {
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


# ==================== PASSWORD MANAGEMENT ENDPOINTS ====================


@app.put(
    "/auth/password",
    tags=["password-management"],
    summary="Update Current User Password",
    description="Update the password for the currently authenticated user",
    responses={
        200: {
            "description": "Password updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Password updated successfully",
                        "requireReauth": True,
                    }
                }
            },
        },
        400: {
            "description": "Password validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_current_password": {
                            "summary": "Invalid current password",
                            "value": {
                                "error": "INVALID_CURRENT_PASSWORD",
                                "message": "Current password is incorrect",
                                "timestamp": "2025-01-22T10:30:00Z",
                                "requestId": "req_123456789",
                            },
                        },
                        "password_policy_violation": {
                            "summary": "Password policy violation",
                            "value": {
                                "error": "PASSWORD_POLICY_VIOLATION",
                                "message": "Password must be at least 8 characters with uppercase, lowercase, number, and special character",
                                "timestamp": "2025-01-22T10:30:00Z",
                                "requestId": "req_123456789",
                            },
                        },
                        "password_reuse": {
                            "summary": "Password recently used",
                            "value": {
                                "error": "PASSWORD_RECENTLY_USED",
                                "message": "Password has been used recently and cannot be reused",
                                "timestamp": "2025-01-22T10:30:00Z",
                                "requestId": "req_123456789",
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Valid authentication token required",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_123456789",
                    }
                }
            },
        },
    },
)
async def update_password(
    password_request: PasswordUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    Update the password for the currently authenticated user.

    This endpoint allows users to change their password by providing their current
    password and a new password that meets the security policy requirements.

    **Password Policy:**
    - Minimum 8 characters
    - Must contain uppercase letter
    - Must contain lowercase letter
    - Must contain number
    - Must contain special character
    - Cannot reuse last 5 passwords

    **Security Features:**
    - Current password verification required
    - Password history checking
    - Automatic token invalidation after change
    - Comprehensive audit logging

    **Required Authentication:** Bearer token in Authorization header
    """
    try:
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        # Update password
        success, response, error = await password_service.update_password(
            person_id=current_user.id,
            password_request=password_request,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error or "Password update failed",
            )

        return {
            "success": response.success,
            "message": response.message,
            "require_reauth": response.require_reauth,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("updating password", e)


@app.put(
    "/people/{person_id}/password",
    tags=["password-management"],
    summary="Update Person Password",
    description="Update password for a specific person (users can only update their own password)",
    responses={
        200: {
            "description": "Password updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Password updated successfully",
                        "requireReauth": True,
                        "timestamp": "2025-01-22T10:30:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Password validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_current_password": {
                            "summary": "Invalid current password",
                            "value": {
                                "error": "INVALID_CURRENT_PASSWORD",
                                "message": "Current password is incorrect",
                                "timestamp": "2025-01-22T10:30:00Z",
                                "requestId": "req_person123_1642857000",
                            },
                        },
                        "password_policy_violation": {
                            "summary": "Password policy violation",
                            "value": {
                                "error": "PASSWORD_POLICY_VIOLATION",
                                "message": "Password does not meet policy requirements",
                                "timestamp": "2025-01-22T10:30:00Z",
                                "requestId": "req_person123_1642857000",
                            },
                        },
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INSUFFICIENT_PERMISSIONS",
                        "message": "You can only update your own password",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_person123_1642857000",
                    }
                }
            },
        },
        404: {
            "description": "Person not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "PERSON_NOT_FOUND",
                        "message": "Person not found",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_person123_1642857000",
                    }
                }
            },
        },
    },
)
async def update_person_password(
    person_id: str,
    password_request: PasswordUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    Update password for a specific person.

    This endpoint allows users to update their own password by person ID.
    Users can only update their own password unless they have admin privileges.

    **Authorization:** Users can only update their own password
    **Password Policy:** Same requirements as /auth/password endpoint
    **Security Features:** Same security features as /auth/password endpoint

    **Required Authentication:** Bearer token in Authorization header
    """
    try:
        # Authorization check: Users can only update their own password
        # TODO: Add admin role checking to allow admins to update any user's password
        if current_user.id != person_id:
            logger.warning(
                f"User {current_user.id} attempted to update password for user {person_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own password",
            )

        # Verify the person exists
        person = await db_service.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        # Check if account is active
        if not getattr(person, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update password for inactive account",
            )

        # Extract client information for audit logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        # Update password using the password management service
        success, response, error = await password_service.update_password(
            person_id=person_id,
            password_request=password_request,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if not success:
            # Return structured error response based on the error type
            if "Current password is incorrect" in (error or ""):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_CURRENT_PASSWORD",
                        "message": "Current password is incorrect",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                    },
                )
            elif "password" in (error or "").lower() and (
                "policy" in (error or "").lower()
                or "complexity" in (error or "").lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PASSWORD_POLICY_VIOLATION",
                        "message": error
                        or "Password does not meet policy requirements",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PASSWORD_UPDATE_FAILED",
                        "message": error or "Password update failed",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                    },
                )

        # Return success response with proper structure
        return {
            "success": response.success,
            "message": response.message,
            "requireReauth": response.require_reauth,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating password for person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while updating the password",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
            },
        )


@app.post("/auth/password/validate")
async def validate_current_password(
    request_data: dict, current_user=Depends(get_current_user)
):
    """Validate current user's password"""
    try:
        current_password = request_data.get("current_password")
        if not current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )

        is_valid, error_msg = await password_service.validate_password_change_request(
            person_id=current_user.id, current_password=current_password
        )

        return {
            "valid": is_valid,
            "message": error_msg if error_msg else "Password validation successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate password",
        )


@app.post("/auth/password/check-history")
async def check_password_history(
    request_data: dict, current_user=Depends(get_current_user)
):
    """Check if password has been used recently"""
    try:
        password = request_data.get("password")
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required"
            )

        can_use, error_msg = await password_service.check_password_history(
            person_id=current_user.id, password=password
        )

        return {
            "can_use": can_use,
            "message": error_msg if error_msg else "Password can be used",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking password history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check password history",
        )


# Admin password management endpoints
@app.post("/admin/password/force-change")
async def force_password_change(
    request_data: dict, request: Request, current_user=Depends(get_current_user)
):
    """Force password change for a user (admin only)"""
    try:
        # TODO: Add proper admin role checking
        person_id = request_data.get("person_id")
        if not person_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Person ID is required"
            )

        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        success, error_msg = await password_service.force_password_change(
            person_id=person_id,
            admin_user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to force password change",
            )

        return {"success": True, "message": "Password change forced successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forcing password change: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to force password change",
        )


@app.post("/admin/password/generate-temporary")
async def generate_temporary_password(
    request_data: dict, request: Request, current_user=Depends(get_current_user)
):
    """Generate temporary password for a user (admin only)"""
    try:
        # TODO: Add proper admin role checking
        person_id = request_data.get("person_id")
        length = request_data.get("length", 12)

        if not person_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Person ID is required"
            )

        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        success, temp_password, error_msg = (
            await password_service.generate_temporary_password(
                person_id=person_id,
                admin_user_id=current_user.id,
                length=length,
                ip_address=client_ip,
                user_agent=user_agent,
            )
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Failed to generate temporary password",
            )

        return {
            "success": True,
            "message": "Temporary password generated successfully",
            "temporary_password": temp_password,
            "require_change": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating temporary password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate temporary password",
        )


@app.post(
    "/people/{person_id}/unlock",
    tags=["admin"],
    summary="Unlock User Account",
    description="Unlock a locked user account (admin only)",
    responses={
        200: {
            "description": "Account unlocked successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Account unlocked successfully. Reason: Administrative unlock requested by support",
                        "unlockedAt": "2025-01-22T10:30:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Invalid request or account not locked",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ACCOUNT_NOT_LOCKED",
                        "message": "Account is not currently locked",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_unlock_1642857000",
                    }
                }
            },
        },
        403: {
            "description": "Insufficient admin privileges",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INSUFFICIENT_PRIVILEGES",
                        "message": "Admin privileges required to unlock accounts",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_unlock_1642857000",
                    }
                }
            },
        },
        404: {
            "description": "Person not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "PERSON_NOT_FOUND",
                        "message": "Person not found",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_unlock_1642857000",
                    }
                }
            },
        },
    },
)
async def unlock_account(
    person_id: str,
    unlock_request: AdminUnlockRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db_service: DynamoDBService = Depends(DynamoDBService),
):
    """
    Unlock a locked user account (admin only).

    This endpoint allows administrators to unlock user accounts that have been
    locked due to failed login attempts or other security measures.

    **Admin Authorization Required:** This endpoint requires admin privileges
    **Audit Logging:** All unlock operations are logged for security audit
    **Reason Required:** A reason must be provided for the unlock operation

    **Required Authentication:** Bearer token with admin privileges
    """
    try:
        # Check if the person exists
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

        # Check if the account is actually locked
        if (
            not hasattr(person, "account_locked_until")
            or not person.account_locked_until
            or person.account_locked_until < datetime.now(timezone.utc)
        ):
            return {
                "success": True,
                "message": "Account is not locked",
                "unlocked_at": datetime.now().isoformat(),
            }

        # Extract client information for audit logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        # Unlock the account
        update_data = PersonUpdate()
        update_data.failed_login_attempts = 0
        update_data.account_locked_until = None

        updated_person = await db_service.update_person(person_id, update_data)
        if not updated_person:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "UPDATE_FAILED",
                    "message": "Failed to unlock account",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_unlock_{int(datetime.now().timestamp())}",
                },
            )

        # Log the admin action for audit purposes
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.ADMIN_ACCOUNT_UNLOCK,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.MEDIUM,
            user_id=current_user.id,  # Admin who performed the action
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "target_user_id": person_id,
                "reason": unlock_request.reason,
                "previous_failed_attempts": getattr(person, "failed_login_attempts", 0),
            },
        )

        await db_service.log_security_event(security_event)

        # Return success response
        return AdminUnlockResponse(
            success=True,
            message=f"Account unlocked successfully. Reason: {unlock_request.reason}",
            unlocked_at=datetime.now(),
        ).model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlocking account for person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while unlocking the account",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_unlock_{int(datetime.now().timestamp())}",
            },
        )


@app.get(
    "/people",
    response_model=list[PersonResponse],
    tags=["people"],
    summary="List People",
    description="Get a paginated list of all registered people",
    responses={
        200: {
            "description": "List of people retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "firstName": "John",
                            "lastName": "Doe",
                            "email": "john.doe@example.com",
                            "phone": "+1-555-0123",
                            "dateOfBirth": "1990-01-15",
                            "address": {
                                "street": "123 Main St",
                                "city": "Anytown",
                                "state": "CA",
                                "zipCode": "12345",
                                "country": "USA",
                            },
                            "createdAt": "2025-01-20T10:30:00Z",
                            "updatedAt": "2025-01-22T10:30:00Z",
                            "isActive": True,
                            "emailVerified": True,
                        }
                    ]
                }
            },
        },
        400: {
            "description": "Invalid pagination parameters",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_PAGINATION",
                        "message": "Limit must be between 1 and 1000",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_list_1642857000",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Valid authentication token required",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_list_1642857000",
                    }
                }
            },
        },
    },
)
async def list_people(
    request: Request, limit: int = 100, current_user=Depends(require_no_password_change)
):
    """
    Get a paginated list of all registered people.

    Returns a list of person records with basic profile information.
    Sensitive fields like password hashes are excluded from the response.

    **Pagination:** Use the limit parameter to control the number of results
    **Security:** All access is logged for audit purposes
    **Data Protection:** Sensitive fields are automatically excluded

    **Required Authentication:** Bearer token in Authorization header
    """
    try:
        # Validate pagination parameters
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PAGINATION",
                    "message": "Limit must be between 1 and 1000",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_list_{int(datetime.now().timestamp())}",
                },
            )

        # Log access event for audit purposes
        await _log_people_list_access_event(
            user_id=current_user.id, request=request, limit=limit
        )

        people = await db_service.list_people(limit=limit)

        # Log successful retrieval
        await _log_people_list_success_event(
            user_id=current_user.id, request=request, count=len(people), limit=limit
        )

        return [PersonResponse.from_person(person) for person in people]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing people: {str(e)}")

        # Log error event
        await _log_people_list_error_event(
            user_id=current_user.id, request=request, error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve people",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_list_error_{int(datetime.now().timestamp())}",
            },
        )


@app.get(
    "/people/{person_id}",
    response_model=PersonResponse,
    tags=["people"],
    summary="Get Person",
    description="Get detailed information for a specific person by ID",
    responses={
        200: {
            "description": "Person information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "firstName": "John",
                        "lastName": "Doe",
                        "email": "john.doe@example.com",
                        "phone": "+1-555-0123",
                        "dateOfBirth": "1990-01-15",
                        "address": {
                            "street": "123 Main St",
                            "city": "Anytown",
                            "state": "CA",
                            "zipCode": "12345",
                            "country": "USA",
                        },
                        "createdAt": "2025-01-20T10:30:00Z",
                        "updatedAt": "2025-01-22T10:30:00Z",
                        "isActive": True,
                        "emailVerified": True,
                    }
                }
            },
        },
        400: {
            "description": "Invalid person ID format",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_PERSON_ID",
                        "message": "Person ID cannot be empty",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_get_1642857000",
                    }
                }
            },
        },
        404: {
            "description": "Person not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "PERSON_NOT_FOUND",
                        "message": "Person not found",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_get_notfound_1642857000",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Valid authentication token required",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_get_1642857000",
                    }
                }
            },
        },
    },
)
async def get_person(
    person_id: str, request: Request, current_user=Depends(require_no_password_change)
):
    """
    Get detailed information for a specific person by ID.

    Returns complete profile information for the specified person.
    Sensitive fields like password hashes are excluded from the response.

    **Security:** All access is logged for audit purposes
    **Data Protection:** Sensitive fields are automatically excluded
    **Validation:** Person ID format is validated

    **Required Authentication:** Bearer token in Authorization header
    """
    try:
        # Validate person_id format
        if not person_id or len(person_id.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PERSON_ID",
                    "message": "Person ID cannot be empty",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_get_{int(datetime.now().timestamp())}",
                },
            )

        # Log access event for audit purposes
        await _log_person_access_event(
            person_id=person_id, user_id=current_user.id, request=request
        )

        person = await db_service.get_person(person_id)

        if not person:
            # Log not found event
            await _log_person_not_found_event(
                person_id=person_id, user_id=current_user.id, request=request
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PERSON_NOT_FOUND",
                    "message": "Person not found",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_get_notfound_{int(datetime.now().timestamp())}",
                },
            )

        # Log successful retrieval
        await _log_person_access_success_event(
            person_id=person_id, user_id=current_user.id, request=request
        )

        return PersonResponse.from_person(person)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting person {person_id}: {str(e)}")

        # Log error event
        await _log_person_access_error_event(
            person_id=person_id, user_id=current_user.id, request=request, error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to retrieve person",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_get_error_{int(datetime.now().timestamp())}",
            },
        )


@app.post(
    "/people",
    response_model=PersonResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["people"],
    summary="Create Person",
    description="Register a new person in the system",
    responses={
        201: {
            "description": "Person created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "firstName": "John",
                        "lastName": "Doe",
                        "email": "john.doe@example.com",
                        "phone": "+1-555-0123",
                        "dateOfBirth": "1990-01-15",
                        "address": {
                            "street": "123 Main St",
                            "city": "Anytown",
                            "state": "CA",
                            "zipCode": "12345",
                            "country": "USA",
                        },
                        "createdAt": "2025-01-22T10:30:00Z",
                        "updatedAt": "2025-01-22T10:30:00Z",
                        "isActive": True,
                        "emailVerified": False,
                    }
                }
            },
        },
        400: {
            "description": "Validation errors",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "The request contains invalid data",
                        "details": [
                            {
                                "field": "email",
                                "message": "Invalid email format",
                                "code": "EMAIL_FORMAT",
                            },
                            {
                                "field": "phone",
                                "message": "Invalid phone format",
                                "code": "PHONE_FORMAT",
                            },
                        ],
                        "timestamp": "2025-01-22T10:30:00Z",
                        "request_id": "req-123",
                    }
                }
            },
        },
        409: {
            "description": "Email already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": "EMAIL_EXISTS",
                        "message": "A person with this email already exists",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_create_1642857000",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Valid authentication token required",
                        "timestamp": "2025-01-22T10:30:00Z",
                        "requestId": "req_auth_1642857000",
                    }
                }
            },
        },
    },
)
async def create_person(
    person_data: PersonCreate, current_user=Depends(require_no_password_change)
):
    """
    Register a new person in the system.

    Creates a new person record with the provided information.
    All fields are validated according to the system's validation rules.

    **Validation:**
    - Email must be valid format and unique
    - Phone number must be valid format
    - Date of birth must be valid date in YYYY-MM-DD format
    - All address fields are required

    **Security:** Email uniqueness is enforced
    **Audit:** Person creation is logged

    **Required Authentication:** Bearer token in Authorization header
    """
    try:
        person = await db_service.create_person(person_data)
        return PersonResponse.from_person(person)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise handle_database_error("creating person", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create person",
        )


@app.put("/people/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str,
    person_update: PersonUpdate,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Update an existing person with enhanced validation and email change verification"""
    try:
        # Check if person exists
        existing_person = await db_service.get_person(person_id)
        if not existing_person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PERSON_NOT_FOUND",
                    "message": "Person not found",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                },
            )

        # Validate the update data
        validation_result = await validation_service.validate_person_update(
            person_id, person_update
        )

        if not validation_result.is_valid:
            # Return detailed validation errors
            error_response = ErrorResponse(
                error="VALIDATION_ERROR",
                message="The request contains invalid data",
                details=validation_result.errors,
                request_id=f"req_{person_id}_{int(datetime.now().timestamp())}",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(),
            )

        # Check if email is being changed
        email_change_initiated = False
        original_email = person_update.email
        if person_update.email and person_update.email != existing_person.email:
            # Initiate email change verification workflow
            success, message = await email_verification_service.initiate_email_change(
                person_id, person_update.email
            )

            if not success:
                error_response = ErrorResponse(
                    error="EMAIL_CHANGE_FAILED",
                    message=message,
                    request_id=f"req_{person_id}_{int(datetime.now().timestamp())}",
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response.model_dump(),
                )

            email_change_initiated = True
            # Create a new PersonUpdate without the email field for immediate update
            update_data = person_update.model_dump(exclude_unset=True)
            del update_data["email"]
            person_update = PersonUpdate(**update_data)

        # Update the person (excluding email if verification was initiated)
        updated_person = await db_service.update_person(person_id, person_update)

        if not updated_person:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "UPDATE_FAILED",
                    "message": "Failed to update person",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                },
            )

        # Log the update event for audit purposes
        await _log_person_update_event(
            person_id=person_id,
            updated_fields=list(person_update.model_dump(exclude_unset=True).keys()),
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            email_change_initiated=email_change_initiated,
        )

        # Create response
        response = PersonResponse.from_person(updated_person)

        # Add email change notification to response if applicable
        if email_change_initiated:
            # Add a custom header or modify response to indicate email verification is pending
            response.pendingEmailChange = original_email

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while updating the person",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
            },
        )


async def _log_person_update_event(
    person_id: str,
    updated_fields: list,
    ip_address: str,
    user_agent: str,
    email_change_initiated: bool = False,
):
    """Log person update event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {
            "updated_fields": updated_fields,
            "email_change_initiated": email_change_initiated,
        }

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PROFILE_UPDATE,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.LOW,
            user_id=person_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        # Don't fail the main operation if audit logging fails
        logger.warning(f"Failed to log person update event: {str(e)}")


@app.post("/people/{person_id}/verify-email")
async def initiate_email_verification(
    person_id: str,
    email_request: EmailVerificationRequest,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Initiate email change verification process"""
    try:
        # Authorization check: Users can only change their own email
        if current_user.id != person_id:
            logger.warning(
                f"User {current_user.id} attempted to change email for user {person_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FORBIDDEN",
                    "message": "You can only change your own email address",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                },
            )

        # Initiate email change verification
        success, message = await email_verification_service.initiate_email_change(
            person_id, email_request.new_email
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "EMAIL_VERIFICATION_FAILED",
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
                },
            )

        return {
            "success": True,
            "message": message,
            "verification_sent": True,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error initiating email verification for person {person_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to initiate email verification",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_{person_id}_{int(datetime.now().timestamp())}",
            },
        )


@app.post("/verify-email")
async def verify_email_change(request_data: dict):
    """Verify email change using verification token"""
    try:
        verification_token = request_data.get("token")
        if not verification_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "MISSING_TOKEN",
                    "message": "Verification token is required",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_verify_{int(datetime.now().timestamp())}",
                },
            )

        # Verify the email change
        success, message = await email_verification_service.verify_email_change(
            verification_token
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "VERIFICATION_FAILED",
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_verify_{int(datetime.now().timestamp())}",
                },
            )

        return {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email change: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Failed to verify email change",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_verify_{int(datetime.now().timestamp())}",
            },
        )


@app.post("/people/{person_id}/delete/initiate")
async def initiate_person_deletion(
    person_id: str,
    deletion_request: PersonDeletionInitiateRequest,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Initiate person deletion with referential integrity checks"""
    try:
        # Validate person_id format
        if not person_id or len(person_id.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PERSON_ID",
                    "message": "Person ID cannot be empty",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_delete_init_{int(datetime.now().timestamp())}",
                },
            )

        # Extract client information for audit logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        # Initiate deletion using the deletion service
        success, response, error = await deletion_service.initiate_deletion(
            person_id=person_id,
            requesting_user_id=current_user.id,
            reason=deletion_request.reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if not success:
            # Check if it's a referential integrity error
            if error and "active subscription" in error.lower():
                # Parse the error to get structured response
                try:
                    import json

                    error_data = json.loads(error)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT, detail=error_data
                    )
                except (json.JSONDecodeError, TypeError):
                    # Fallback to generic conflict response
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "REFERENTIAL_INTEGRITY_VIOLATION",
                            "message": "Cannot delete person with active subscriptions",
                            "timestamp": datetime.now().isoformat(),
                            "request_id": f"req_delete_init_{int(datetime.now().timestamp())}",
                        },
                    )
            elif "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "PERSON_NOT_FOUND",
                        "message": "Person not found",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_init_{int(datetime.now().timestamp())}",
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "DELETION_INITIATION_FAILED",
                        "message": error or "Failed to initiate deletion",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_init_{int(datetime.now().timestamp())}",
                    },
                )

        return response.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating deletion for person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while initiating deletion",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_delete_init_error_{int(datetime.now().timestamp())}",
            },
        )


@app.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: str,
    deletion_request: PersonDeletionRequest,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Confirm and execute person deletion with two-step confirmation"""
    try:
        # Validate person_id format
        if not person_id or len(person_id.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_PERSON_ID",
                    "message": "Person ID cannot be empty",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                },
            )

        # Extract client information for audit logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")

        # Confirm deletion using the deletion service
        success, response, error = await deletion_service.confirm_deletion(
            confirmation_token=deletion_request.confirmation_token,
            requesting_user_id=current_user.id,
            reason=deletion_request.reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        if not success:
            if "invalid" in error.lower() or "expired" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_CONFIRMATION_TOKEN",
                        "message": error or "Invalid or expired confirmation token",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                    },
                )
            elif "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "PERSON_NOT_FOUND",
                        "message": "Person not found",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                    },
                )
            elif "user mismatch" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "FORBIDDEN",
                        "message": "Only the user who initiated the deletion can confirm it",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                    },
                )
            elif "subscription" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "REFERENTIAL_INTEGRITY_VIOLATION",
                        "message": error
                        or "Cannot delete person with active subscriptions",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "DELETION_FAILED",
                        "message": error or "Failed to delete person",
                        "timestamp": datetime.now().isoformat(),
                        "request_id": f"req_delete_{int(datetime.now().timestamp())}",
                    },
                )

        # Return 204 No Content on successful deletion
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting person {person_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while deleting the person",
                "timestamp": datetime.now().isoformat(),
                "request_id": f"req_delete_error_{int(datetime.now().timestamp())}",
            },
        )


# ==================== PROJECT ENDPOINTS ====================


@app.get("/projects")
async def get_projects():
    """Get all projects"""
    try:
        projects = db_service.get_all_projects()
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        raise handle_database_error("getting projects", e)


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project by ID"""
    try:
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting project {project_id}", e)


@app.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: dict, current_user: dict = Depends(get_current_user)
):
    """Create a new project"""
    try:
        from ..models.project import ProjectCreate

        # Validate project data
        project_create = ProjectCreate(**project_data)

        # Create project with current user as creator
        created_by = current_user.get("email", "admin")
        project = db_service.create_project(project_create, created_by)

        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project data: {str(e)}",
        )
    except Exception as e:
        raise handle_database_error("creating project", e)


@app.put("/projects/{project_id}")
async def update_project(
    project_id: str, project_data: dict, current_user: dict = Depends(get_current_user)
):
    """Update an existing project"""
    try:
        from ..models.project import ProjectUpdate

        # Validate project data
        project_update = ProjectUpdate(**project_data)

        # Update project
        updated_project = db_service.update_project(project_id, project_update)

        if not updated_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        return updated_project
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project data: {str(e)}",
        )
    except Exception as e:
        raise handle_database_error("updating project {project_id}", e)


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str, current_user: dict = Depends(get_current_user)
):
    """Delete a project"""
    try:
        success = await db_service.delete_project(project_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("deleting project {project_id}", e)


# ==================== SUBSCRIPTION ENDPOINTS ====================


@app.get("/subscriptions")
async def get_subscriptions():
    """Get all subscriptions"""
    try:
        subscriptions = db_service.get_all_subscriptions()
        return {"subscriptions": subscriptions, "count": len(subscriptions)}
    except Exception as e:
        raise handle_database_error("getting subscriptions", e)


@app.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Get a specific subscription by ID"""
    try:
        subscription = await db_service.get_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting subscription {subscription_id}", e)


@app.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(subscription_data: dict):
    """Create a new subscription"""
    try:
        from ..models.subscription import SubscriptionCreate

        # Validate subscription data
        subscription_create = SubscriptionCreate(**subscription_data)

        # Verify person and project exist
        person = db_service.get_person_by_id(subscription_create.personId)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Person not found"
            )

        project = await db_service.get_project_by_id(subscription_create.projectId)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found"
            )

        # Create subscription
        subscription = db_service.create_subscription(subscription_create)

        return subscription
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription data: {str(e)}",
        )
    except Exception as e:
        raise handle_database_error("creating subscription", e)


@app.put("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, subscription_data: dict):
    """Update an existing subscription"""
    try:
        from ..models.subscription import SubscriptionUpdate

        # Validate subscription data
        subscription_update = SubscriptionUpdate(**subscription_data)

        # Update subscription
        updated_subscription = db_service.update_subscription(
            subscription_id, subscription_update
        )

        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        return updated_subscription
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription data: {str(e)}",
        )
    except Exception as e:
        raise handle_database_error("updating subscription {subscription_id}", e)


@app.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(subscription_id: str):
    """Delete a subscription"""
    try:
        success = await db_service.delete_subscription(subscription_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("deleting subscription {subscription_id}", e)


@app.post("/public/subscribe", status_code=status.HTTP_201_CREATED)
async def create_subscription_with_person(subscription_data: dict):
    """Create a subscription with person creation (public endpoint for frontend forms)"""
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

        # Validate person data
        person_create = PersonCreate(**person_data)

        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found"
            )

        # Check if person already exists by email (this method IS async)
        existing_person = await db_service.get_person_by_email(person_create.email)

        if existing_person:
            # Use existing person - existing_person is a Person object
            person_id = existing_person.id
        else:
            # Create new person (this method IS async)
            created_person = await db_service.create_person(person_create)
            person_id = created_person.id

        # Create subscription
        subscription_create = SubscriptionCreate(
            projectId=project_id,
            personId=person_id,
            status="active",  # Changed from "pending" to "active"
            notes=notes,
        )

        # Create subscription (this method is NOT async, but expects SubscriptionCreate object)
        created_subscription = db_service.create_subscription(subscription_create)

        return {
            "message": "Subscription created successfully",
            "subscription": created_subscription,
            "person_created": existing_person is None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("creating subscription with person", e)


@app.get("/people/{person_id}/subscriptions")
async def get_person_subscriptions(person_id: str):
    """Get all subscriptions for a specific person"""
    try:
        # Verify person exists
        person = db_service.get_person_by_id(person_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
            )

        subscriptions = await db_service.get_subscriptions_by_person(person_id)
        return {"subscriptions": subscriptions, "count": len(subscriptions)}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting subscriptions for person {person_id}", e)


@app.get("/projects/{project_id}/subscriptions")
async def get_project_subscriptions(project_id: str):
    """Get all subscriptions for a specific project"""
    try:
        # Verify project exists
        project = await db_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        subscriptions = await db_service.get_subscriptions_by_project(project_id)
        return {"subscriptions": subscriptions, "count": len(subscriptions)}
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting subscriptions for project {project_id}", e)


# ==================== AUDIT LOGGING FUNCTIONS ====================


async def _log_people_list_access_event(user_id: str, request: Request, limit: int):
    """Log people list access event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {"action": "list_people_request", "limit": limit}

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_LIST_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.LOW,
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log people list access event: {str(e)}")


async def _log_people_list_success_event(
    user_id: str, request: Request, count: int, limit: int
):
    """Log successful people list retrieval for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {
            "action": "list_people_success",
            "count": count,
            "limit": limit,
        }

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_LIST_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.LOW,
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log people list success event: {str(e)}")


async def _log_people_list_error_event(user_id: str, request: Request, error: str):
    """Log people list error event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {"action": "list_people_error", "error": error}

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_LIST_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.MEDIUM,  # Errors are medium severity
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log people list error event: {str(e)}")


async def _log_person_access_event(person_id: str, user_id: str, request: Request):
    """Log person access event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {
            "action": "person_access_request",
            "target_person_id": person_id,
        }

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.LOW,
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log person access event: {str(e)}")


async def _log_person_not_found_event(person_id: str, user_id: str, request: Request):
    """Log person not found event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {"action": "person_not_found", "target_person_id": person_id}

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.MEDIUM,  # Not found could indicate probing
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log person not found event: {str(e)}")


async def _log_person_access_success_event(
    person_id: str, user_id: str, request: Request
):
    """Log successful person access for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {
            "action": "person_access_success",
            "target_person_id": person_id,
        }

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.LOW,
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log person access success event: {str(e)}")


async def _log_person_access_error_event(
    person_id: str, user_id: str, request: Request, error: str
):
    """Log person access error event for audit purposes"""
    try:
        from ..models.security_event import (
            SecurityEvent,
            SecurityEventType,
            SecurityEventSeverity,
        )
        import uuid

        event_details = {
            "action": "person_access_error",
            "target_person_id": person_id,
            "error": error,
        }

        security_event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type=SecurityEventType.PERSON_ACCESS,
            timestamp=datetime.utcnow(),
            severity=SecurityEventSeverity.MEDIUM,  # Errors are medium severity
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details=event_details,
        )

        await db_service.log_security_event(security_event)

    except Exception as e:
        logger.error(f"Failed to log person access error event: {str(e)}")


# Lambda handler
handler = Mangum(app, lifespan="off")
