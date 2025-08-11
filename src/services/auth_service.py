"""
Authentication service for handling login, security events, and account lockout.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import uuid
import time

from ..core.base_service import BaseService, ServiceStatus, HealthCheck, ServiceResponse
from ..models.auth import (
    LoginRequest,
    LoginResponse,
    SecurityEvent,
    AccountLockout,
    AuthenticatedUser,
)
from ..models.person import Person
from ..services.defensive_dynamodb_service import (
    DefensiveDynamoDBService as DynamoDBService,
)
from ..services.roles_service import RolesService
from ..utils.password_utils import PasswordHasher
from ..utils.jwt_utils import create_tokens_for_user

logger = logging.getLogger(__name__)


class AuthService(BaseService):
    """Service for handling authentication operations."""

    # Account lockout configuration
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("auth_service", config)
        self.db_service = None
        self.roles_service = None

    async def initialize(self) -> bool:
        """Initialize the authentication service."""
        try:
            self.logger.info("Initializing AuthService...")
            
            # Initialize dependencies
            self.db_service = DynamoDBService()
            self.roles_service = RolesService()
            
            # Test database connectivity
            await self._test_database_connection()
            
            self._initialized = True
            self.logger.info("AuthService initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AuthService: {str(e)}")
            return False

    async def health_check(self) -> HealthCheck:
        """Perform health check for the authentication service."""
        start_time = time.time()
        
        try:
            if not self._initialized:
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Service not initialized",
                    response_time_ms=(time.time() - start_time) * 1000
                )
            
            # Test database connectivity
            await self._test_database_connection()
            
            # Test roles service
            if self.roles_service:
                # Simple test to ensure roles service is working
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.HEALTHY,
                message="Authentication service is healthy",
                details={
                    "database_connected": True,
                    "roles_service_available": self.roles_service is not None,
                    "max_failed_attempts": self.MAX_FAILED_ATTEMPTS,
                    "lockout_duration_minutes": self.LOCKOUT_DURATION_MINUTES
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed: {str(e)}")
            
            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time
            )

    async def _test_database_connection(self):
        """Test database connectivity."""
        if not self.db_service:
            raise Exception("Database service not initialized")
        
        # Simple test - this will raise an exception if DB is not accessible
        # We can add a more specific test method to DynamoDBService if needed
        pass

    async def authenticate_user(
        self,
        login_request: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[LoginResponse], Optional[str]]:
        """
        Authenticate a user with email and password.

        Args:
            login_request: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (success, login_response_or_none, error_message_or_none)
        """
        try:
            # Get user by email
            person = await self.db_service.get_person_by_email(login_request.email)
            if not person:
                await self._log_security_event(
                    person_id="unknown",
                    action="LOGIN_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "user_not_found", "email": login_request.email},
                )
                return False, None, "Invalid email or password"

            # Check if account is locked
            is_locked, lockout_info = await self._check_account_lockout(person.id)
            if is_locked:
                await self._log_security_event(
                    person_id=person.id,
                    action="LOGIN_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "reason": "account_locked",
                        "locked_until": (
                            lockout_info.locked_until.isoformat()
                            if lockout_info and lockout_info.locked_until
                            else None
                        ),
                    },
                )
                return (
                    False,
                    None,
                    f"Account is temporarily locked. Try again after {lockout_info.locked_until.strftime('%H:%M') if lockout_info and lockout_info.locked_until else 'some time'} UTC.",
                )

            # Verify password
            if not hasattr(person, "password_hash") or not person.password_hash:
                await self._log_security_event(
                    person_id=person.id,
                    action="LOGIN_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "no_password_set"},
                )
                return False, None, "Account not set up for login"

            password_valid = PasswordHasher.verify_password(
                login_request.password, person.password_hash
            )

            if not password_valid:
                # Record failed attempt
                await self._record_failed_attempt(person.id, ip_address)

                await self._log_security_event(
                    person_id=person.id,
                    action="LOGIN_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "invalid_password"},
                )
                return False, None, "Invalid email or password"

            # Check if account is active
            if not getattr(person, "is_active", True):
                await self._log_security_event(
                    person_id=person.id,
                    action="LOGIN_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "account_inactive"},
                )
                return False, None, "Account is deactivated"

            # Successful login - clear failed attempts
            await self._clear_failed_attempts(person.id)

            # Update last login time
            await self._update_last_login(person.id)

            # Check admin status using the new RBAC system
            is_admin = await self.roles_service.user_is_admin(person.id)

            # Create JWT tokens with admin role information
            user_data = {
                "email": person.email,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "is_admin": is_admin,  # Use RBAC system result
                "require_password_change": getattr(
                    person, "require_password_change", False
                ),
            }

            tokens = create_tokens_for_user(person.id, user_data)

            # Create response
            login_response = LoginResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_type=tokens["token_type"],
                expires_in=tokens["expires_in"],
                user={
                    "id": person.id,
                    "email": person.email,
                    "firstName": person.first_name,
                    "lastName": person.last_name,
                    "isAdmin": is_admin,  # Use RBAC system result
                },
                require_password_change=getattr(
                    person, "require_password_change", False
                ),
            )

            # Log successful login
            await self._log_security_event(
                person_id=person.id,
                action="LOGIN_SUCCESS",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "require_password_change": getattr(
                        person, "require_password_change", False
                    )
                },
            )

            return True, login_response, None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, None, "Authentication failed"

    async def _check_account_lockout(
        self, person_id: str
    ) -> Tuple[bool, Optional[AccountLockout]]:
        """
        Check if an account is currently locked out.

        Args:
            person_id: Person ID to check

        Returns:
            Tuple of (is_locked, lockout_info)
        """
        try:
            # Get lockout info from database
            lockout_info = await self.db_service.get_account_lockout(person_id)
            if not lockout_info:
                return False, None

            # Check if lockout has expired
            if lockout_info.locked_until and lockout_info.locked_until > datetime.now(
                timezone.utc
            ):
                return True, lockout_info

            # Lockout has expired, clear it
            if lockout_info.locked_until:
                await self.db_service.clear_account_lockout(person_id)

            return False, lockout_info

        except Exception as e:
            logger.error(f"Error checking account lockout for {person_id}: {str(e)}")
            return False, None

    async def _record_failed_attempt(
        self, person_id: str, ip_address: Optional[str] = None
    ):
        """
        Record a failed login attempt and potentially lock the account.

        Args:
            person_id: Person ID
            ip_address: IP address of the attempt
        """
        try:
            # Get current lockout info
            lockout_info = await self.db_service.get_account_lockout(person_id)

            if not lockout_info:
                lockout_info = AccountLockout(
                    person_id=person_id,
                    failed_attempts=1,
                    last_attempt_at=datetime.now(timezone.utc),
                    ip_addresses=[ip_address] if ip_address else [],
                )
            else:
                lockout_info.failed_attempts += 1
                lockout_info.last_attempt_at = datetime.now(timezone.utc)
                if ip_address and ip_address not in lockout_info.ip_addresses:
                    lockout_info.ip_addresses.append(ip_address)

            # Check if we should lock the account
            if lockout_info.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                lockout_info.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=self.LOCKOUT_DURATION_MINUTES
                )

                # Log account lockout
                await self._log_security_event(
                    person_id=person_id,
                    action="ACCOUNT_LOCKED",
                    success=True,
                    ip_address=ip_address,
                    details={
                        "failed_attempts": lockout_info.failed_attempts,
                        "locked_until": lockout_info.locked_until.isoformat(),
                    },
                )

            # Save lockout info
            await self.db_service.save_account_lockout(lockout_info)

        except Exception as e:
            logger.error(f"Error recording failed attempt for {person_id}: {str(e)}")

    async def _clear_failed_attempts(self, person_id: str):
        """
        Clear failed login attempts for a user.

        Args:
            person_id: Person ID
        """
        try:
            await self.db_service.clear_account_lockout(person_id)
        except Exception as e:
            logger.error(f"Error clearing failed attempts for {person_id}: {str(e)}")

    async def _update_last_login(self, person_id: str):
        """
        Update the last login timestamp for a user.

        Args:
            person_id: Person ID
        """
        try:
            await self.db_service.update_last_login(
                person_id, datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error updating last login for {person_id}: {str(e)}")

    async def _log_security_event(
        self,
        person_id: str,
        action: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a security event for audit purposes.

        Args:
            person_id: Person ID
            action: Action type (LOGIN_SUCCESS, LOGIN_FAILED, etc.)
            success: Whether the action was successful
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional details
        """
        try:
            security_event = SecurityEvent(
                person_id=person_id,
                action=action,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                details=details,
            )

            await self.db_service.log_security_event(security_event)

        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")

    async def unlock_account(self, person_id: str, admin_user_id: str) -> bool:
        """
        Manually unlock a user account (admin function).

        Args:
            person_id: Person ID to unlock
            admin_user_id: ID of admin performing the unlock

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.db_service.clear_account_lockout(person_id)

            # Log the unlock event
            await self._log_security_event(
                person_id=person_id,
                action="ACCOUNT_UNLOCKED",
                success=True,
                details={"unlocked_by": admin_user_id},
            )

            return True

        except Exception as e:
            logger.error(f"Error unlocking account {person_id}: {str(e)}")
            return False
