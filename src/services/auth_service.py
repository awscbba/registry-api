"""
Authentication service implementation.
Handles business logic for authentication operations.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..core.config import config
from ..repositories.people_repository import PeopleRepository
from ..models.auth import LoginResponse, User
from ..models.person import PersonResponse
from ..utils.password_utils import (
    PasswordHasher,
    PasswordValidator,
    hash_and_validate_password,
)


class AuthService:
    """Service for authentication business logic."""

    def __init__(self):
        self.people_repository = PeopleRepository()
        self.jwt_secret = config.auth.jwt_secret
        self.jwt_algorithm = config.auth.jwt_algorithm
        self.access_token_expire_hours = config.auth.access_token_expire_hours

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return PasswordHasher.hash_password(password)

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return PasswordHasher.verify_password(password, hashed_password)

    def _generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT access token."""
        expiry_time = datetime.utcnow() + timedelta(
            hours=self.access_token_expire_hours
        )

        # Log token expiration for debugging
        from ..services.logging_service import logging_service, LogLevel, LogCategory

        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM_EVENTS,
            message=f"Generating access token with {self.access_token_expire_hours}h expiry",
            additional_data={
                "user_id": user_data["id"],
                "expires_at": expiry_time.isoformat(),
                "expires_in_hours": self.access_token_expire_hours,
            },
        )

        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "isAdmin": user_data.get("isAdmin", False),
            "exp": expiry_time,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT refresh token."""
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "exp": datetime.utcnow()
            + timedelta(days=config.auth.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[LoginResponse]:
        """Authenticate a user with email and password."""
        # Get user data with password hash for authentication
        person_data = self.people_repository.get_by_email_for_auth(email)
        if not person_data:
            return None

        # Check if user is active
        if not person_data.get("isActive", False):
            return None

        # Verify password hash exists
        password_hash = person_data.get("passwordHash")
        if not password_hash:
            # Log failed login attempt
            from ..security.authorization import authorization_service

            authorization_service.record_failed_login(person_data.get("id"))

            from ..services.logging_service import (
                logging_service,
                LogCategory,
                LogLevel,
            )

            logging_service.log_authentication_event(
                event_type="login_failed",
                user_id=person_data.get("id"),
                success=False,
                details={"reason": "no_password_hash", "email": email},
            )
            return None

        # Verify password against hash
        if not self._verify_password(password, password_hash):
            # Record failed login attempt
            from ..security.authorization import authorization_service

            authorization_service.record_failed_login(person_data.get("id"))

            from ..services.logging_service import (
                logging_service,
                LogCategory,
                LogLevel,
            )

            logging_service.log_authentication_event(
                event_type="login_failed",
                user_id=person_data.get("id"),
                success=False,
                details={"reason": "invalid_password", "email": email},
            )
            return None

        # Generate tokens
        # Create clean user data without password hash for token generation
        clean_user_data = {k: v for k, v in person_data.items() if k != "passwordHash"}
        access_token = self._generate_access_token(clean_user_data)
        refresh_token = self._generate_refresh_token(clean_user_data)

        # Get user roles from RBAC service
        from ..services.service_registry_manager import get_rbac_service

        rbac_service = get_rbac_service()
        user_roles = await rbac_service.get_user_roles(person_data.get("id"))
        role_names = [role.value for role in user_roles]

        # Temporary fix: Add super_admin for specific user
        if person_data.get("id") == "4a375abe-6d1a-47bc-98ff-ced6f8247c1b":
            if "super_admin" not in role_names:
                role_names.append("super_admin")

        # Create user response
        user_response = {
            "id": person_data.get("id"),
            "email": person_data.get("email"),
            "firstName": person_data.get("firstName"),
            "lastName": person_data.get("lastName"),
            "phone": person_data.get("phone", ""),
            "dateOfBirth": person_data.get("dateOfBirth", ""),
            "address": person_data.get("address", {}),
            "isAdmin": person_data.get("isAdmin", False),
            "isActive": person_data.get("isActive", True),
            "roles": role_names,
        }

        # Clear any failed login attempts on successful login
        from ..security.authorization import authorization_service

        authorization_service.clear_failed_attempts(person_data.get("id"))

        # Log successful login
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        logging_service.log_authentication_event(
            event_type="login_success",
            user_id=person_data.get("id"),
            success=True,
            details={
                "email": person_data.get("email"),
                "user_roles": [],  # Will be populated by RBAC service
            },
        )

        return LoginResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            user=user_response,
            expiresIn=self.access_token_expire_hours * 3600,
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        person = self.people_repository.get_by_id(user_id)
        if not person:
            return None

        # Get user roles from RBAC service
        from ..services.service_registry_manager import get_rbac_service

        rbac_service = get_rbac_service()
        user_roles = await rbac_service.get_user_roles(person.id)
        role_names = [role.value for role in user_roles]

        return User(
            id=person.id,
            email=person.email,
            firstName=person.firstName,
            lastName=person.lastName,
            phone=person.phone or "",
            dateOfBirth=person.dateOfBirth or "",
            address=person.address.model_dump() if person.address else {},
            isAdmin=person.isAdmin,
            isActive=person.isActive,
            roles=role_names,
        )

    async def refresh_access_token(self, refresh_token: str) -> Optional[LoginResponse]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        person = self.people_repository.get_by_id(user_id)
        if not person or not person.isActive:
            return None

        # Generate new tokens
        user_data = person.model_dump()
        access_token = self._generate_access_token(user_data)
        new_refresh_token = self._generate_refresh_token(user_data)

        # Get user roles from RBAC service
        from ..services.service_registry_manager import get_rbac_service

        rbac_service = get_rbac_service()
        user_roles = await rbac_service.get_user_roles(person.id)
        role_names = [role.value for role in user_roles]

        user_response = {
            "id": person.id,
            "email": person.email,
            "firstName": person.firstName,
            "lastName": person.lastName,
            "isAdmin": person.isAdmin,
            "isActive": person.isActive,
            "roles": role_names,
        }

        return LoginResponse(
            accessToken=access_token,
            refreshToken=new_refresh_token,
            user=user_response,
            expiresIn=self.access_token_expire_hours * 3600,
        )

    def _generate_reset_token(self, user_data: Dict[str, Any]) -> str:
        """Generate password reset token."""
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "exp": datetime.utcnow()
            + timedelta(hours=1),  # Reset token expires in 1 hour
            "iat": datetime.utcnow(),
            "type": "password_reset",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """Initiate password reset process."""
        # Get user by email
        person = self.people_repository.get_by_email(email)
        if not person:
            # Return success even if email doesn't exist (security best practice)
            return {
                "message": "If the email exists, a password reset link has been sent",
                "email": email,
            }

        # Check if user is active
        if not person.isActive:
            return {
                "message": "If the email exists, a password reset link has been sent",
                "email": email,
            }

        # Generate reset token
        user_data = person.model_dump()
        reset_token = self._generate_reset_token(user_data)

        # Send password reset email
        from .email_service import EmailService

        email_service = EmailService()

        email_result = await email_service.send_password_reset_email(
            email=email, first_name=person.firstName, reset_token=reset_token
        )

        if email_result["success"]:
            return {
                "message": "Password reset link has been sent to your email",
                "email": email,
            }
        else:
            # Log the error but still return success for security
            return {
                "message": "If the email exists, a password reset link has been sent",
                "email": email,
            }

    async def validate_reset_token(self, token: str) -> bool:
        """Validate password reset token."""
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "password_reset":
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        # Verify user still exists and is active
        person = self.people_repository.get_by_id(user_id)
        if not person or not person.isActive:
            return False

        return True

    async def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Reset user password using reset token."""

        # Validate password strength (basic validation)
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Validate reset token
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "password_reset":
            raise ValueError("Invalid or expired reset token")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid reset token")

        # Get user
        person = self.people_repository.get_by_id(user_id)
        if not person or not person.isActive:
            raise ValueError("User not found or inactive")

        # Validate and hash the new password
        is_valid, hashed_password, validation_errors = hash_and_validate_password(
            new_password
        )

        if not is_valid:
            raise ValueError(
                f"Password validation failed: {', '.join(validation_errors)}"
            )

        # Update the password in the database
        # Note: This would require updating the person repository to support password updates
        # For now, we'll simulate success but this needs to be implemented

        # Update password in database
        from ..models.person import PersonUpdate

        update_data = PersonUpdate(
            passwordHash=hashed_password,
            requirePasswordChange=False,
            lastPasswordChange=__import__("datetime").datetime.utcnow(),
        )

        updated_person = self.people_repository.update(user_id, update_data)
        if not updated_person:
            raise ValueError("Failed to update password in database")

        return {
            "message": "Password has been reset successfully",
            "userId": user_id,
            "email": person.email,
        }
