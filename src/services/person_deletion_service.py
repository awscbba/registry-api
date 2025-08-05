"""
Person Deletion Service
Handles secure person deletion with referential integrity checks and two-step confirmation
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any

from ..models.person import PersonDeletionResponse, ReferentialIntegrityError
from ..models.security_event import (
    SecurityEvent,
    SecurityEventType,
    SecurityEventSeverity,
)
from .defensive_dynamodb_service import DefensiveDynamoDBService as DynamoDBService

logger = logging.getLogger(__name__)


class PersonDeletionService:
    """Service for handling secure person deletion operations"""

    def __init__(self, db_service: DynamoDBService):
        self.db_service = db_service
        # Store pending deletions in memory (in production, use Redis or DynamoDB)
        self._pending_deletions: Dict[str, Dict[str, Any]] = {}
        self.confirmation_timeout_minutes = 15  # Token expires after 15 minutes

    async def initiate_deletion(
        self,
        person_id: str,
        requesting_user_id: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, PersonDeletionResponse, Optional[str]]:
        """
        Initiate person deletion with referential integrity checks

        Returns:
            Tuple of (success, response, error_message)
        """
        try:
            # Check if person exists
            person = await self.db_service.get_person(person_id)
            if not person:
                return (
                    False,
                    PersonDeletionResponse(success=False, message="Person not found"),
                    "Person not found",
                )

            # Check for existing subscriptions
            subscriptions = await self.db_service.get_subscriptions_by_person(person_id)
            active_subscriptions = [
                sub
                for sub in subscriptions
                if sub.get("status") in ["active", "pending"]
            ]

            if active_subscriptions:
                # Create referential integrity error response
                related_records = []
                for sub in active_subscriptions:
                    project = await self.db_service.get_project_by_id(
                        sub.get("projectId", "")
                    )
                    related_records.append(
                        {
                            "subscription_id": sub.get("id"),
                            "project_id": sub.get("projectId"),
                            "project_name": (
                                project.get("name", "Unknown") if project else "Unknown"
                            ),
                            "status": sub.get("status"),
                            "created_at": sub.get("createdAt"),
                        }
                    )

                error_response = ReferentialIntegrityError(
                    message=f"Cannot delete person with {len(active_subscriptions)} active subscription(s). Please cancel or transfer subscriptions first.",
                    constraint_type="subscriptions",
                    related_records=related_records,
                )

                # Log the referential integrity violation
                await self._log_deletion_event(
                    person_id=person_id,
                    requesting_user_id=requesting_user_id,
                    event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                    success=False,
                    details={
                        "reason": "referential_integrity_violation",
                        "constraint_type": "subscriptions",
                        "active_subscriptions_count": len(active_subscriptions),
                        "reason_provided": reason,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return (
                    False,
                    PersonDeletionResponse(
                        success=False,
                        message=error_response.message,
                        subscriptions_found=len(active_subscriptions),
                    ),
                    error_response.model_dump_json(),
                )

            # Generate confirmation token
            confirmation_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(
                minutes=self.confirmation_timeout_minutes
            )

            # Store pending deletion
            self._pending_deletions[confirmation_token] = {
                "person_id": person_id,
                "requesting_user_id": requesting_user_id,
                "reason": reason,
                "expires_at": expires_at,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow(),
            }

            # Log deletion initiation
            await self._log_deletion_event(
                person_id=person_id,
                requesting_user_id=requesting_user_id,
                event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                success=True,
                details={
                    "stage": "initiation",
                    "confirmation_token": confirmation_token,
                    "expires_at": expires_at.isoformat(),
                    "reason_provided": reason,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return (
                True,
                PersonDeletionResponse(
                    success=True,
                    message="Deletion initiated. Please confirm with the provided token within 15 minutes.",
                    confirmation_token=confirmation_token,
                    expires_at=expires_at,
                    subscriptions_found=0,
                ),
                None,
            )

        except Exception as e:
            logger.error(f"Error initiating deletion for person {person_id}: {str(e)}")

            # Log error event
            await self._log_deletion_event(
                person_id=person_id,
                requesting_user_id=requesting_user_id,
                event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                success=False,
                details={
                    "stage": "initiation",
                    "error": str(e),
                    "reason_provided": reason,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return (
                False,
                PersonDeletionResponse(
                    success=False, message="Failed to initiate deletion"
                ),
                f"Internal error: {str(e)}",
            )

    async def confirm_deletion(
        self,
        confirmation_token: str,
        requesting_user_id: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, PersonDeletionResponse, Optional[str]]:
        """
        Confirm and execute person deletion

        Returns:
            Tuple of (success, response, error_message)
        """
        try:
            # Validate confirmation token
            if confirmation_token not in self._pending_deletions:
                return (
                    False,
                    PersonDeletionResponse(
                        success=False, message="Invalid or expired confirmation token"
                    ),
                    "Invalid confirmation token",
                )

            pending_deletion = self._pending_deletions[confirmation_token]

            # Check if token has expired
            if datetime.utcnow() > pending_deletion["expires_at"]:
                # Clean up expired token
                del self._pending_deletions[confirmation_token]
                return (
                    False,
                    PersonDeletionResponse(
                        success=False,
                        message="Confirmation token has expired. Please initiate deletion again.",
                    ),
                    "Token expired",
                )

            person_id = pending_deletion["person_id"]
            original_requesting_user_id = pending_deletion["requesting_user_id"]

            # Verify the same user is confirming
            if requesting_user_id != original_requesting_user_id:
                return (
                    False,
                    PersonDeletionResponse(
                        success=False,
                        message="Only the user who initiated the deletion can confirm it",
                    ),
                    "User mismatch",
                )

            # Double-check person still exists
            person = await self.db_service.get_person(person_id)
            if not person:
                # Clean up token
                del self._pending_deletions[confirmation_token]
                return (
                    False,
                    PersonDeletionResponse(
                        success=False, message="Person no longer exists"
                    ),
                    "Person not found",
                )

            # Final check for subscriptions (in case they were added between initiation and confirmation)
            subscriptions = await self.db_service.get_subscriptions_by_person(person_id)
            active_subscriptions = [
                sub
                for sub in subscriptions
                if sub.get("status") in ["active", "pending"]
            ]

            if active_subscriptions:
                # Clean up token
                del self._pending_deletions[confirmation_token]

                related_records = []
                for sub in active_subscriptions:
                    project = await self.db_service.get_project_by_id(
                        sub.get("projectId", "")
                    )
                    related_records.append(
                        {
                            "subscription_id": sub.get("id"),
                            "project_id": sub.get("projectId"),
                            "project_name": (
                                project.get("name", "Unknown") if project else "Unknown"
                            ),
                            "status": sub.get("status"),
                            "created_at": sub.get("createdAt"),
                        }
                    )

                # Log the referential integrity violation at confirmation
                await self._log_deletion_event(
                    person_id=person_id,
                    requesting_user_id=requesting_user_id,
                    event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                    success=False,
                    details={
                        "stage": "confirmation",
                        "reason": "referential_integrity_violation_at_confirmation",
                        "constraint_type": "subscriptions",
                        "active_subscriptions_count": len(active_subscriptions),
                        "confirmation_token": confirmation_token,
                        "reason_provided": reason or pending_deletion.get("reason"),
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return (
                    False,
                    PersonDeletionResponse(
                        success=False,
                        message=f"Cannot delete person with {len(active_subscriptions)} active subscription(s) that were created after deletion initiation. Please cancel subscriptions and try again.",
                        subscriptions_found=len(active_subscriptions),
                    ),
                    "New subscriptions found",
                )

            # Perform the actual deletion
            deletion_successful = await self.db_service.delete_person(person_id)

            if not deletion_successful:
                # Clean up token
                del self._pending_deletions[confirmation_token]

                await self._log_deletion_event(
                    person_id=person_id,
                    requesting_user_id=requesting_user_id,
                    event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                    success=False,
                    details={
                        "stage": "confirmation",
                        "reason": "database_deletion_failed",
                        "confirmation_token": confirmation_token,
                        "reason_provided": reason or pending_deletion.get("reason"),
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                return (
                    False,
                    PersonDeletionResponse(
                        success=False, message="Failed to delete person from database"
                    ),
                    "Database deletion failed",
                )

            # Log successful deletion
            await self._log_deletion_event(
                person_id=person_id,
                requesting_user_id=requesting_user_id,
                event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                success=True,
                details={
                    "stage": "completion",
                    "confirmation_token": confirmation_token,
                    "person_email": person.email,
                    "person_name": f"{person.first_name} {person.last_name}",
                    "reason_provided": reason or pending_deletion.get("reason"),
                    "initiated_at": pending_deletion["created_at"].isoformat(),
                    "confirmed_at": datetime.utcnow().isoformat(),
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Clean up token
            del self._pending_deletions[confirmation_token]

            return (
                True,
                PersonDeletionResponse(
                    success=True,
                    message=f"Person {person.email} has been successfully deleted",
                ),
                None,
            )

        except Exception as e:
            logger.error(
                f"Error confirming deletion with token {confirmation_token}: {str(e)}"
            )

            # Clean up token on error
            if confirmation_token in self._pending_deletions:
                pending_deletion = self._pending_deletions[confirmation_token]
                person_id = pending_deletion.get("person_id", "unknown")

                await self._log_deletion_event(
                    person_id=person_id,
                    requesting_user_id=requesting_user_id,
                    event_type=SecurityEventType.ACCOUNT_DEACTIVATED,
                    success=False,
                    details={
                        "stage": "confirmation",
                        "error": str(e),
                        "confirmation_token": confirmation_token,
                        "reason_provided": reason,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                del self._pending_deletions[confirmation_token]

            return (
                False,
                PersonDeletionResponse(
                    success=False, message="Failed to confirm deletion"
                ),
                f"Internal error: {str(e)}",
            )

    async def _log_deletion_event(
        self,
        person_id: str,
        requesting_user_id: str,
        event_type: SecurityEventType,
        success: bool,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log deletion-related security events"""
        try:
            security_event = SecurityEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                severity=(
                    SecurityEventSeverity.HIGH
                    if success
                    else SecurityEventSeverity.CRITICAL
                ),
                user_id=requesting_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "target_person_id": person_id,
                    "operation": "person_deletion",
                    **details,
                },
            )

            await self.db_service.log_security_event(security_event)

        except Exception as e:
            # Don't fail the main operation if audit logging fails
            logger.warning(f"Failed to log deletion event: {str(e)}")

    def cleanup_expired_tokens(self):
        """Clean up expired confirmation tokens (should be called periodically)"""
        current_time = datetime.utcnow()
        expired_tokens = [
            token
            for token, data in self._pending_deletions.items()
            if current_time > data["expires_at"]
        ]

        for token in expired_tokens:
            logger.info(f"Cleaning up expired deletion token: {token}")
            del self._pending_deletions[token]

        return len(expired_tokens)

    def get_pending_deletions_count(self) -> int:
        """Get count of pending deletions (for monitoring)"""
        return len(self._pending_deletions)
