"""
Password Reset Service

Handles password reset functionality including token generation,
validation, and password updates with security measures.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import uuid
import bcrypt

from ..core.base_service import BaseService, ServiceResponse, HealthCheck, ServiceStatus
from ..models.password_reset import (
    PasswordResetToken,
    PasswordResetRequest,
    PasswordResetValidation,
    PasswordResetResponse,
)
from ..models.person import Person
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..services.email_service import EmailService
from ..services.rate_limiting_service import check_password_reset_rate_limit
from ..core.config import get_config

logger = logging.getLogger(__name__)


class PasswordResetService(BaseService):
    """Service for handling password reset operations."""

    def __init__(
        self,
        db_service: DefensiveDynamoDBService = None,
        email_service: EmailService = None,
    ):
        super().__init__("password_reset")
        self.db_service = db_service
        self.email_service = email_service
        self.config = get_config()
        self._initialized = True

    async def initialize(self) -> bool:
        """Initialize the password reset service"""
        try:
            # Verify configuration is available
            if not self.config:
                self.logger.error("Configuration not available")
                return False

            self.logger.info("Password reset service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize password reset service: {str(e)}")
            return False

    async def health_check(self) -> HealthCheck:
        """Check service health"""
        try:
            # Basic health check - verify dependencies are available
            if not self.email_service:
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Email service not available",
                )

            if not self.db_service:
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Database service not available",
                )

            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.HEALTHY,
                message="Password reset service is operational",
            )
        except Exception as e:
            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
            )

    async def initiate_password_reset(
        self, request: PasswordResetRequest
    ) -> PasswordResetResponse:
        """
        Initiate password reset process by generating token and sending email.

        Args:
            request: Password reset request with email and metadata

        Returns:
            PasswordResetResponse with success status and message
        """
        try:
            # Check rate limiting
            from ..models.error_handling import ErrorContext

            context = ErrorContext(
                operation="password_reset_initiation",
                resource_type="password_reset",
                resource_id=request.email,
                user_id=None,
                ip_address=request.ip_address,
                request_id="password_reset_request",  # Add required field with string value
            )

            rate_limit_result = await check_password_reset_rate_limit(
                request.email, context
            )
            if not rate_limit_result.allowed:
                return PasswordResetResponse(
                    success=False,
                    message=f"Too many password reset attempts. Try again in {rate_limit_result.retry_after} seconds.",
                )

            # Find user by email - use people service from service registry
            person = None

            # First try using the injected db_service (people service)
            if self.db_service and hasattr(self.db_service, "get_person_by_email"):
                try:
                    person_result = await self.db_service.get_person_by_email(
                        request.email
                    )
                    # The people service returns a dict, extract the person data
                    if isinstance(person_result, dict) and person_result.get("success"):
                        person_data = person_result.get("data")
                        if person_data:
                            # Convert dict to object-like structure for compatibility
                            class PersonObj:
                                def __init__(self, data):
                                    for key, value in data.items():
                                        setattr(self, key, value)
                                    # Ensure required attributes exist
                                    if not hasattr(self, "is_active"):
                                        self.is_active = True
                                    if not hasattr(self, "first_name") and hasattr(
                                        self, "firstName"
                                    ):
                                        self.first_name = self.firstName
                                    if not hasattr(self, "email") and hasattr(
                                        self, "email"
                                    ):
                                        self.email = self.email

                            person = PersonObj(person_data)
                            logger.info(
                                f"Found user via people service: {person.email}"
                            )
                except Exception as e:
                    # get_person_by_email raises HTTPException for not found, but that's expected
                    # We need to check if it's a 404 (not found) vs other errors
                    if hasattr(e, "status_code") and e.status_code == 404:
                        logger.info(
                            f"User not found via people service: {request.email}"
                        )
                        person = None
                    else:
                        logger.warning(f"Failed to get person via db_service: {str(e)}")
                        person = None

            if not person:
                # Fallback: try direct repository access (legacy path)
                try:
                    from .people_service import PeopleService

                    people_service = PeopleService()

                    # Initialize the people service if needed
                    if hasattr(people_service, "initialize"):
                        await people_service.initialize()

                    # Use the people service repository to get user by email
                    person_result = await people_service.user_repository.get_by_email(
                        request.email
                    )
                    if person_result.success and person_result.data:
                        person = person_result.data
                        logger.info(f"Found user via repository: {person.email}")
                except Exception as e:
                    logger.warning(f"Failed to get person via repository: {str(e)}")
                    person = None

            if not person:
                # Don't reveal if email exists - always return success for security
                logger.warning(
                    f"Password reset requested for non-existent email: {request.email}"
                )
                return PasswordResetResponse(
                    success=True,
                    message="If the email exists in our system, you will receive a password reset link.",
                )

            # Check if account is active
            if not getattr(person, "is_active", True):
                logger.warning(
                    f"Password reset requested for inactive account: {request.email}"
                )
                return PasswordResetResponse(
                    success=False,
                    message="Account is deactivated. Please contact support.",
                )

            # Generate reset token
            reset_token = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=24
            )  # 24 hour expiry - gives users more time to reset password

            # Create reset token record
            token_record = PasswordResetToken(
                reset_token=reset_token,
                person_id=person.id,
                email=person.email,
                expires_at=expires_at,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
            )

            # Save token to database
            await self._save_reset_token(token_record)

            # Send reset email
            email_result = await self.email_service.send_password_reset_email(
                email=person.email,
                first_name=person.first_name,
                reset_token=reset_token,
                expires_at=expires_at,
            )

            if not email_result.success:
                logger.error(
                    f"Failed to send password reset email to {person.email}: {email_result.message}"
                )
                return PasswordResetResponse(
                    success=False,
                    message="Failed to send reset email. Please try again later.",
                )

            logger.info(f"Password reset initiated for {person.email}")
            return PasswordResetResponse(
                success=True,
                message="If the email exists in our system, you will receive a password reset link.",
            )

        except Exception as e:
            logger.error(f"Error initiating password reset: {str(e)}")
            return PasswordResetResponse(
                success=False,
                message="An error occurred. Please try again later.",
            )

    async def validate_reset_token(
        self, reset_token: str
    ) -> Tuple[bool, Optional[PasswordResetToken]]:
        """
        Validate a password reset token.

        Args:
            reset_token: Token to validate

        Returns:
            Tuple of (is_valid, token_record)
        """
        try:
            # Get token from database
            token_record = await self._get_reset_token(reset_token)
            if not token_record:
                return False, None

            # Check if token is already used
            if token_record.is_used:
                logger.warning(
                    f"Attempt to use already used reset token: {reset_token}"
                )
                return False, None

            # Check if token is expired
            if datetime.now(timezone.utc) > token_record.expires_at:
                logger.warning(f"Attempt to use expired reset token: {reset_token}")
                return False, None

            return True, token_record

        except Exception as e:
            logger.error(f"Error validating reset token: {str(e)}")
            return False, None

    async def complete_password_reset(
        self, validation: PasswordResetValidation
    ) -> PasswordResetResponse:
        """
        Complete password reset by updating password and marking token as used.

        Args:
            validation: Reset validation with token and new password

        Returns:
            PasswordResetResponse with success status
        """
        try:
            # Validate token
            is_valid, token_record = await self.validate_reset_token(
                validation.reset_token
            )
            if not is_valid or not token_record:
                return PasswordResetResponse(
                    success=False,
                    message="Invalid or expired reset token.",
                    token_valid=False,
                )

            # Get person
            person = await self.db_service.get_person(token_record.person_id)
            if not person:
                logger.error(
                    f"Person not found for reset token: {token_record.person_id}"
                )
                return PasswordResetResponse(
                    success=False,
                    message="Invalid reset request.",
                    token_valid=False,
                )

            # Validate new password strength
            if len(validation.new_password) < 8:
                return PasswordResetResponse(
                    success=False,
                    message="Password must be at least 8 characters long.",
                    token_valid=True,
                )

            # Hash new password
            password_hash = bcrypt.hashpw(
                validation.new_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            # Update person's password using PersonUpdate object
            from ..models.person import PersonUpdate

            person_update = PersonUpdate(
                password_hash=password_hash,
                require_password_change=False,
                failed_login_attempts=0,
            )

            await self.db_service.update_person(person.id, person_update)

            # Mark token as used
            await self._mark_token_used(validation.reset_token)

            logger.info(f"Password reset completed for person: {person.id}")
            return PasswordResetResponse(
                success=True,
                message="Password has been reset successfully. You can now log in with your new password.",
                token_valid=True,
            )

        except Exception as e:
            logger.error(f"Error completing password reset: {str(e)}")
            return PasswordResetResponse(
                success=False,
                message="An error occurred while resetting password. Please try again.",
            )

    async def _save_reset_token(self, token_record: PasswordResetToken) -> None:
        """Save password reset token to database."""
        # Use the password_reset_tokens table from config
        table_name = self.config.database.password_reset_tokens_table

        # Convert to DynamoDB item format - use camelCase to match table schema
        item = {
            "resetToken": token_record.reset_token,  # Primary key - must match table schema
            "personId": token_record.person_id,
            "email": token_record.email,
            "expiresAt": token_record.expires_at.isoformat(),
            "isUsed": token_record.is_used,
            "createdAt": token_record.created_at.isoformat(),
        }

        if token_record.ip_address:
            item["ipAddress"] = token_record.ip_address
        if token_record.user_agent:
            item["userAgent"] = token_record.user_agent

        # Save to DynamoDB
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        table.put_item(Item=item)

    async def _get_reset_token(self, reset_token: str) -> Optional[PasswordResetToken]:
        """Get password reset token from database."""
        try:
            table_name = self.config.database.password_reset_tokens_table

            import boto3

            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(table_name)

            response = table.get_item(
                Key={"resetToken": reset_token}
            )  # Use camelCase key

            if "Item" not in response:
                return None

            item = response["Item"]

            return PasswordResetToken(
                reset_token=item["resetToken"],  # Use camelCase field names
                person_id=item["personId"],
                email=item["email"],
                expires_at=datetime.fromisoformat(item["expiresAt"]),
                is_used=item.get("isUsed", False),
                created_at=datetime.fromisoformat(item["createdAt"]),
                ip_address=item.get("ipAddress"),
                user_agent=item.get("userAgent"),
            )

        except Exception as e:
            logger.error(f"Error getting reset token: {str(e)}")
            return None

    async def _mark_token_used(self, reset_token: str) -> None:
        """Mark password reset token as used."""
        try:
            table_name = self.config.database.password_reset_tokens_table

            import boto3

            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(table_name)

            table.update_item(
                Key={"resetToken": reset_token},  # Use camelCase key
                UpdateExpression="SET isUsed = :used",  # Use camelCase field name
                ExpressionAttributeValues={":used": True},
            )

        except Exception as e:
            logger.error(f"Error marking token as used: {str(e)}")
            raise
