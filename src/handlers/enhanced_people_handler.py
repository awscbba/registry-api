"""
Enhanced People Handler with comprehensive error handling and logging.
This demonstrates the integration of the new error handling and logging system.
"""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from ..models.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PasswordUpdateRequest,
    PersonSearchRequest,
    PersonSearchResponse,
    EmailVerificationRequest,
)
from ..models.auth import LoginRequest, LoginResponse
from ..models.error_handling import APIException, ErrorCode
from ..models.security_event import SecurityEventType
from ..services.dynamodb_service import DynamoDBService
from ..services.auth_service import AuthService
from ..services.password_management_service import PasswordManagementService
from ..services.person_validation_service import PersonValidationService
from ..services.email_verification_service import EmailVerificationService
from ..services.rate_limiting_service import RateLimitType
from ..middleware.auth_middleware import get_current_user, require_no_password_change
from ..middleware.error_handler_middleware import ErrorHandlerMiddleware
from ..middleware.rate_limit_middleware import RateLimitMiddleware
from ..utils.handler_utils import (
    create_error_context,
    log_person_operation_with_context,
    log_authentication_with_context,
    log_password_event_with_context,
    log_security_event_with_context,
    check_rate_limit_for_endpoint,
    create_person_not_found_exception,
    create_validation_exception_from_errors,
    create_authentication_exception,
    create_password_policy_exception,
    create_email_already_exists_exception,
    handle_service_error,
    log_person_list_access,
    log_person_access,
    log_person_update_audit,
)

# Initialize FastAPI app
app = FastAPI(
    title="People Register API - Enhanced",
    description="API for managing people registration with comprehensive error handling",
    version="2.0.0",
)

# Add error handling middleware
app.add_middleware(ErrorHandlerMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "people-register-api-enhanced"}


# Authentication endpoints with enhanced error handling


@app.post("/auth/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request):
    """Authenticate user and return JWT tokens with comprehensive logging and rate limiting."""
    # Check rate limits for login attempts
    await check_rate_limit_for_endpoint(RateLimitType.LOGIN_ATTEMPTS, request)

    try:
        # Log login attempt
        await log_authentication_with_context(
            event_type="LOGIN_ATTEMPT", user_email=login_request.email, request=request
        )

        # Get client information
        context = create_error_context(request)

        # Authenticate user
        success, login_response, error_message = await auth_service.authenticate_user(
            login_request, context.ip_address, context.user_agent
        )

        if not success:
            # Log failed login
            await log_authentication_with_context(
                event_type="LOGIN_FAILED",
                user_email=login_request.email,
                request=request,
                success=False,
                failure_reason=error_message,
            )

            # Log security event for failed login
            await log_security_event_with_context(
                event_type=SecurityEventType.LOGIN_FAILED,
                request=request,
                details={"email": login_request.email, "failure_reason": error_message},
            )

            raise create_authentication_exception(
                message=error_message or "Authentication failed", request=request
            )

        # Log successful login
        await log_authentication_with_context(
            event_type="LOGIN_SUCCESS",
            user_email=login_request.email,
            request=request,
            success=True,
        )

        # Log security event for successful login
        await log_security_event_with_context(
            event_type=SecurityEventType.LOGIN_SUCCESS,
            request=request,
            user_id=(
                login_response.user_id if hasattr(login_response, "user_id") else None
            ),
            details={"email": login_request.email},
        )

        return login_response

    except APIException:
        raise
    except Exception as e:
        # Handle unexpected errors
        raise await handle_service_error(e, "login", request)


@app.get("/auth/me")
async def get_current_user_info(
    request: Request, current_user=Depends(get_current_user)
):
    """Get current authenticated user information with audit logging."""
    try:
        # Log user info access
        await log_person_operation_with_context(
            operation="GET_USER_INFO",
            person_id=current_user.id,
            request=request,
            user_id=current_user.id,
            success=True,
        )

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

    except Exception as e:
        raise await handle_service_error(e, "get_user_info", request, current_user.id)


# Password management endpoints with enhanced security


@app.put("/auth/password")
async def update_password(
    password_request: PasswordUpdateRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Update current user's password with comprehensive security logging."""
    # Check rate limits for password changes
    await check_rate_limit_for_endpoint(
        RateLimitType.PASSWORD_CHANGE, request, current_user.id
    )

    try:
        # Log password change attempt
        await log_password_event_with_context(
            event_type="PASSWORD_CHANGE_ATTEMPT",
            person_id=current_user.id,
            request=request,
            success=True,
        )

        # Get context for service call
        context = create_error_context(request, current_user.id)

        # Update password
        success, response, error = await password_service.update_password(
            person_id=current_user.id,
            password_request=password_request,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
        )

        if not success:
            # Log failed password change
            await log_password_event_with_context(
                event_type="PASSWORD_CHANGE_FAILED",
                person_id=current_user.id,
                request=request,
                success=False,
                details={"error": error},
            )

            # Determine appropriate exception type
            if "Current password is incorrect" in (error or ""):
                raise APIException(
                    error_code=ErrorCode.INVALID_CURRENT_PASSWORD,
                    message="Current password is incorrect",
                    context=context,
                )
            elif "password" in (error or "").lower() and (
                "policy" in (error or "").lower()
                or "complexity" in (error or "").lower()
            ):
                raise create_password_policy_exception(
                    message=error or "Password does not meet policy requirements",
                    request=request,
                    user_id=current_user.id,
                )
            else:
                raise APIException(
                    error_code=ErrorCode.PASSWORD_UPDATE_FAILED,
                    message=error or "Password update failed",
                    context=context,
                )

        # Log successful password change
        await log_password_event_with_context(
            event_type="PASSWORD_CHANGED",
            person_id=current_user.id,
            request=request,
            success=True,
        )

        # Log security event
        await log_security_event_with_context(
            event_type=SecurityEventType.PASSWORD_CHANGED,
            request=request,
            user_id=current_user.id,
        )

        return {
            "success": response.success,
            "message": response.message,
            "requireReauth": response.require_reauth,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except APIException:
        raise
    except Exception as e:
        raise await handle_service_error(e, "update_password", request, current_user.id)


# Person CRUD operations with comprehensive logging


@app.get("/people", response_model=List[PersonResponse])
async def list_people(
    request: Request, limit: int = 100, current_user=Depends(require_no_password_change)
):
    """List all registered people with audit logging and rate limiting."""
    # Check rate limits
    await check_rate_limit_for_endpoint(
        RateLimitType.API_REQUESTS, request, current_user.id
    )

    try:
        # Validate pagination parameters
        if limit < 1 or limit > 1000:
            raise APIException(
                error_code=ErrorCode.INVALID_VALUE,
                message="Limit must be between 1 and 1000",
                context=create_error_context(request, current_user.id),
            )

        # Get people from database
        people = await db_service.list_people(limit=limit)

        # Log successful access
        await log_person_list_access(
            request=request,
            user_id=current_user.id,
            count=len(people),
            limit=limit,
            success=True,
        )

        # Convert to response models
        return [PersonResponse.from_person(person) for person in people]

    except APIException:
        raise
    except Exception as e:
        # Log failed access
        await log_person_list_access(
            request=request,
            user_id=current_user.id,
            count=0,
            limit=limit,
            success=False,
        )
        raise await handle_service_error(e, "list_people", request, current_user.id)


@app.get("/people/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: str, request: Request, current_user=Depends(require_no_password_change)
):
    """Get a specific person by ID with comprehensive audit logging."""
    # Check rate limits
    await check_rate_limit_for_endpoint(
        RateLimitType.API_REQUESTS, request, current_user.id
    )

    try:
        # Validate person_id format
        if not person_id or len(person_id.strip()) == 0:
            raise APIException(
                error_code=ErrorCode.INVALID_VALUE,
                message="Person ID cannot be empty",
                context=create_error_context(request, current_user.id),
            )

        # Get person from database
        person = await db_service.get_person(person_id)

        if not person:
            # Log not found access
            await log_person_access(
                person_id=person_id,
                request=request,
                user_id=current_user.id,
                success=False,
            )

            raise create_person_not_found_exception(person_id, request)

        # Log successful access
        await log_person_access(
            person_id=person_id, request=request, user_id=current_user.id, success=True
        )

        return PersonResponse.from_person(person)

    except APIException:
        raise
    except Exception as e:
        raise await handle_service_error(e, "get_person", request, current_user.id)


@app.post("/people", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    person_data: PersonCreate,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Create a new person with comprehensive validation and logging."""
    # Check rate limits for person creation
    await check_rate_limit_for_endpoint(
        RateLimitType.PERSON_CREATION, request, current_user.id
    )

    try:
        # Validate person data
        validation_result = await validation_service.validate_person_create(person_data)

        if not validation_result.is_valid:
            field_errors = {
                error.field: error.message for error in validation_result.errors
            }
            raise create_validation_exception_from_errors(
                field_errors=field_errors, request=request, user_id=current_user.id
            )

        # Create person
        person = await db_service.create_person(person_data)

        # Log successful creation
        await log_person_operation_with_context(
            operation="CREATE",
            person_id=person.id,
            request=request,
            user_id=current_user.id,
            success=True,
            details={"created_by": current_user.id},
        )

        return PersonResponse.from_person(person)

    except APIException:
        raise
    except ValueError as e:
        if "already exists" in str(e).lower():
            raise create_email_already_exists_exception(
                email=person_data.email, request=request, user_id=current_user.id
            )
        raise await handle_service_error(e, "create_person", request, current_user.id)
    except Exception as e:
        raise await handle_service_error(e, "create_person", request, current_user.id)


@app.put("/people/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str,
    person_update: PersonUpdate,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Update an existing person with enhanced validation and audit logging."""
    # Check rate limits for person updates
    await check_rate_limit_for_endpoint(
        RateLimitType.PERSON_UPDATES, request, current_user.id
    )

    try:
        # Check if person exists and get current state
        existing_person = await db_service.get_person(person_id)
        if not existing_person:
            raise create_person_not_found_exception(person_id, request)

        # Store before state for audit
        before_state = {
            "email": existing_person.email,
            "first_name": existing_person.first_name,
            "last_name": existing_person.last_name,
            "phone": existing_person.phone,
        }

        # Validate the update data
        validation_result = await validation_service.validate_person_update(
            person_id, person_update
        )

        if not validation_result.is_valid:
            field_errors = {
                error.field: error.message for error in validation_result.errors
            }
            raise create_validation_exception_from_errors(
                field_errors=field_errors, request=request, user_id=current_user.id
            )

        # Handle email change verification if needed
        email_change_initiated = False
        original_email = person_update.email
        if person_update.email and person_update.email != existing_person.email:
            # Initiate email change verification workflow
            success, message = await email_verification_service.initiate_email_change(
                person_id, person_update.email
            )

            if not success:
                raise APIException(
                    error_code=ErrorCode.EMAIL_VERIFICATION_FAILED,
                    message=message,
                    context=create_error_context(request, current_user.id),
                )

            email_change_initiated = True
            # Remove email from immediate update
            update_data = person_update.model_dump(exclude_unset=True)
            del update_data["email"]
            person_update = PersonUpdate(**update_data)

        # Update the person
        updated_person = await db_service.update_person(person_id, person_update)

        if not updated_person:
            raise APIException(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to update person",
                context=create_error_context(request, current_user.id),
            )

        # Store after state for audit
        after_state = {
            "email": updated_person.email,
            "first_name": updated_person.first_name,
            "last_name": updated_person.last_name,
            "phone": updated_person.phone,
            "email_change_initiated": email_change_initiated,
        }

        # Log the update for audit trail
        await log_person_update_audit(
            person_id=person_id,
            request=request,
            user_id=current_user.id,
            before_state=before_state,
            after_state=after_state,
            success=True,
        )

        # Create response
        response = PersonResponse.from_person(updated_person)

        # Add email change notification if applicable
        if email_change_initiated:
            response.pendingEmailChange = original_email

        return response

    except APIException:
        raise
    except Exception as e:
        raise await handle_service_error(e, "update_person", request, current_user.id)


@app.get("/people/search", response_model=PersonSearchResponse)
async def search_people(
    request: Request,
    email: str = None,
    first_name: str = None,
    last_name: str = None,
    phone: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user=Depends(require_no_password_change),
):
    """Search for people with filtering capabilities and comprehensive logging."""
    # Check rate limits for search requests
    await check_rate_limit_for_endpoint(
        RateLimitType.SEARCH_REQUESTS, request, current_user.id
    )

    try:
        # Create search request
        search_request = PersonSearchRequest(
            email=email,
            firstName=first_name,
            lastName=last_name,
            phone=phone,
            limit=limit,
            offset=offset,
        )

        # Perform search (this would need to be implemented in the database service)
        # For now, we'll use a placeholder implementation
        people = await db_service.list_people(limit=limit)  # Placeholder

        # Log search operation
        await log_person_operation_with_context(
            operation="SEARCH",
            person_id="multiple",
            request=request,
            user_id=current_user.id,
            success=True,
            details={
                "search_criteria": search_request.model_dump(exclude_unset=True),
                "results_count": len(people),
            },
        )

        # Create search response
        return PersonSearchResponse.create(
            people=people,
            total_count=len(people),  # This would be the actual total from database
            limit=limit,
            offset=offset,
        )

    except APIException:
        raise
    except Exception as e:
        raise await handle_service_error(e, "search_people", request, current_user.id)


# Email verification endpoint


@app.post("/people/{person_id}/verify-email")
async def initiate_email_verification(
    person_id: str,
    email_request: EmailVerificationRequest,
    request: Request,
    current_user=Depends(require_no_password_change),
):
    """Initiate email change verification process with rate limiting."""
    # Check rate limits for email verification
    await check_rate_limit_for_endpoint(
        RateLimitType.EMAIL_VERIFICATION, request, current_user.id
    )

    try:
        # Authorization check: Users can only change their own email
        if current_user.id != person_id:
            await log_security_event_with_context(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                request=request,
                user_id=current_user.id,
                details={
                    "attempted_person_id": person_id,
                    "action": "email_verification",
                    "reason": "user_attempted_to_change_another_users_email",
                },
            )

            raise APIException(
                error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                message="You can only change your own email address",
                context=create_error_context(request, current_user.id),
            )

        # Initiate email change verification
        success, message = await email_verification_service.initiate_email_change(
            person_id, email_request.new_email
        )

        if not success:
            raise APIException(
                error_code=ErrorCode.EMAIL_VERIFICATION_FAILED,
                message=message,
                context=create_error_context(request, current_user.id),
            )

        # Log successful email verification initiation
        await log_person_operation_with_context(
            operation="EMAIL_VERIFICATION_INITIATED",
            person_id=person_id,
            request=request,
            user_id=current_user.id,
            success=True,
            details={"new_email": email_request.new_email},
        )

        return {
            "success": True,
            "message": message,
            "verification_sent": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except APIException:
        raise
    except Exception as e:
        raise await handle_service_error(
            e, "initiate_email_verification", request, current_user.id
        )


# Export the app for use in Lambda
handler = app
