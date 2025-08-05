"""
Password management service for handling secure password operations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

from ..models.person import Person, PasswordUpdateRequest, PasswordUpdateResponse
from ..models.auth import SecurityEvent
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService as DynamoDBService
from ..utils.password_utils import (
    PasswordValidator,
    PasswordHasher,
    PasswordHistoryManager,
    PasswordGenerator,
    hash_and_validate_password,
)

logger = logging.getLogger(__name__)


class PasswordManagementService:
    """Service for managing password operations with security and validation."""

    def __init__(self):
        self.db_service = DynamoDBService()

    async def update_password(
        self,
        person_id: str,
        password_request: PasswordUpdateRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, PasswordUpdateResponse, Optional[str]]:
        """
        Update a person's password with validation and security checks.

        Args:
            person_id: ID of the person updating password
            password_request: Password update request with current and new passwords
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (success, response, error_message)
        """
        try:
            # Get the person from database
            person = await self.db_service.get_person(person_id)
            if not person:
                await self._log_security_event(
                    person_id=person_id,
                    action="PASSWORD_UPDATE_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "person_not_found"},
                )
                return (
                    False,
                    PasswordUpdateResponse(success=False, message="Person not found"),
                    "Person not found",
                )

            # Validate current password
            if not await self._validate_current_password(
                person, password_request.current_password
            ):
                await self._log_security_event(
                    person_id=person_id,
                    action="PASSWORD_UPDATE_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "invalid_current_password"},
                )
                return (
                    False,
                    PasswordUpdateResponse(
                        success=False, message="Current password is incorrect"
                    ),
                    "Current password is incorrect",
                )

            # Validate new password against policy and history
            is_valid, hashed_password, validation_errors = (
                await self._validate_new_password(person, password_request.new_password)
            )

            if not is_valid:
                await self._log_security_event(
                    person_id=person_id,
                    action="PASSWORD_UPDATE_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "reason": "password_validation_failed",
                        "errors": validation_errors,
                    },
                )
                return (
                    False,
                    PasswordUpdateResponse(
                        success=False, message="; ".join(validation_errors)
                    ),
                    "; ".join(validation_errors),
                )

            # Update password in database
            success = await self._update_password_in_database(
                person_id, hashed_password, person.password_history or []
            )

            if not success:
                await self._log_security_event(
                    person_id=person_id,
                    action="PASSWORD_UPDATE_FAILED",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "database_update_failed"},
                )
                return (
                    False,
                    PasswordUpdateResponse(
                        success=False, message="Failed to update password"
                    ),
                    "Failed to update password",
                )

            # Log successful password update
            await self._log_security_event(
                person_id=person_id,
                action="PASSWORD_UPDATED",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"require_reauth": True},
            )

            return (
                True,
                PasswordUpdateResponse(
                    success=True,
                    message="Password updated successfully",
                    require_reauth=True,
                ),
                None,
            )

        except Exception as e:
            logger.error(f"Error updating password for person {person_id}: {str(e)}")
            await self._log_security_event(
                person_id=person_id,
                action="PASSWORD_UPDATE_FAILED",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "system_error", "error": str(e)},
            )
            return (
                False,
                PasswordUpdateResponse(success=False, message="System error occurred"),
                "System error occurred",
            )

    async def validate_password_change_request(
        self, person_id: str, current_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a password change request by verifying the current password.

        Args:
            person_id: ID of the person
            current_password: Current password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            person = await self.db_service.get_person(person_id)
            if not person:
                return False, "Person not found"

            is_valid = await self._validate_current_password(person, current_password)
            if not is_valid:
                return False, "Current password is incorrect"

            return True, None

        except Exception as e:
            logger.error(
                f"Error validating password change request for person {person_id}: {str(e)}"
            )
            return False, "System error occurred"

    async def force_password_change(
        self,
        person_id: str,
        admin_user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Force a password change requirement for a person (admin function).

        Args:
            person_id: ID of the person
            admin_user_id: ID of admin forcing the change
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (success, error_message)
        """
        try:
            person = await self.db_service.get_person(person_id)
            if not person:
                return False, "Person not found"

            # Update require_password_change flag
            success = await self._update_password_change_requirement(person_id, True)

            if success:
                await self._log_security_event(
                    person_id=person_id,
                    action="PASSWORD_CHANGE_FORCED",
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"forced_by": admin_user_id},
                )
                return True, None
            else:
                return False, "Failed to force password change"

        except Exception as e:
            logger.error(
                f"Error forcing password change for person {person_id}: {str(e)}"
            )
            return False, "System error occurred"

    async def generate_temporary_password(
        self,
        person_id: str,
        admin_user_id: str,
        length: int = 12,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a temporary password for a person (admin function).

        Args:
            person_id: ID of the person
            admin_user_id: ID of admin generating the password
            length: Length of temporary password
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (success, temporary_password, error_message)
        """
        try:
            person = await self.db_service.get_person(person_id)
            if not person:
                return False, None, "Person not found"

            # Generate secure temporary password
            temp_password = PasswordGenerator.generate_secure_password(length)
            hashed_password = PasswordHasher.hash_password(temp_password)

            # Update password in database and force password change
            success = await self._update_password_in_database(
                person_id,
                hashed_password,
                person.password_history or [],
                require_change=True,
            )

            if success:
                await self._log_security_event(
                    person_id=person_id,
                    action="TEMPORARY_PASSWORD_GENERATED",
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"generated_by": admin_user_id, "require_change": True},
                )
                return True, temp_password, None
            else:
                return False, None, "Failed to set temporary password"

        except Exception as e:
            logger.error(
                f"Error generating temporary password for person {person_id}: {str(e)}"
            )
            return False, None, "System error occurred"

    async def check_password_history(
        self, person_id: str, password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a password has been used recently.

        Args:
            person_id: ID of the person
            password: Password to check

        Returns:
            Tuple of (can_use_password, error_message)
        """
        try:
            person = await self.db_service.get_person(person_id)
            if not person:
                return False, "Person not found"

            can_use, error_msg = PasswordHistoryManager.can_use_password(
                password, person.password_history or []
            )

            return can_use, error_msg if not can_use else None

        except Exception as e:
            logger.error(
                f"Error checking password history for person {person_id}: {str(e)}"
            )
            return False, "System error occurred"

    async def _validate_current_password(
        self, person: Person, current_password: str
    ) -> bool:
        """
        Validate the current password for a person.

        Args:
            person: Person object
            current_password: Current password to validate

        Returns:
            True if password is valid, False otherwise
        """
        if not hasattr(person, "password_hash") or not person.password_hash:
            return False

        return PasswordHasher.verify_password(current_password, person.password_hash)

    async def _validate_new_password(
        self, person: Person, new_password: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate a new password against policy and history.

        Args:
            person: Person object
            new_password: New password to validate

        Returns:
            Tuple of (is_valid, hashed_password_or_empty, list_of_errors)
        """
        return hash_and_validate_password(new_password, person.password_history or [])

    async def _update_password_in_database(
        self,
        person_id: str,
        hashed_password: str,
        current_history: List[str],
        require_change: bool = False,
    ) -> bool:
        """
        Update password in the database with history management.

        Args:
            person_id: ID of the person
            hashed_password: New hashed password
            current_history: Current password history
            require_change: Whether to require password change on next login

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update password history
            updated_history = PasswordHistoryManager.add_to_history(
                current_history, hashed_password
            )

            # Prepare update expression
            now = datetime.now(timezone.utc)
            update_expression = """
                SET passwordHash = :password_hash,
                    passwordHistory = :password_history,
                    lastPasswordChange = :last_change,
                    updatedAt = :updated_at
            """

            expression_values = {
                ":password_hash": hashed_password,
                ":password_history": updated_history,
                ":last_change": now.isoformat(),
                ":updated_at": now.isoformat(),
            }

            if require_change:
                update_expression += ", requirePasswordChange = :require_change"
                expression_values[":require_change"] = True

            # Update in DynamoDB
            self.db_service.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
            )

            return True

        except Exception as e:
            logger.error(
                f"Error updating password in database for person {person_id}: {str(e)}"
            )
            return False

    async def _update_password_change_requirement(
        self, person_id: str, require_change: bool
    ) -> bool:
        """
        Update the password change requirement flag.

        Args:
            person_id: ID of the person
            require_change: Whether to require password change

        Returns:
            True if successful, False otherwise
        """
        try:
            self.db_service.table.update_item(
                Key={"id": person_id},
                UpdateExpression="SET requirePasswordChange = :require_change, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ":require_change": require_change,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Error updating password change requirement for person {person_id}: {str(e)}"
            )
            return False

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
            action: Action type
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
