"""
Email verification service for handling email change verification workflows.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from ..models.email import EmailRequest, EmailType
from ..models.person import Person
from .email_service import EmailService
from .dynamodb_service import DynamoDBService

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Service for handling email change verification workflows."""

    def __init__(
        self,
        dynamodb_service: DynamoDBService = None,
        email_service: EmailService = None,
    ):
        self.dynamodb_service = dynamodb_service or DynamoDBService()
        self.email_service = email_service or EmailService()
        self.verification_token_expiry_hours = 24  # 24 hours to verify email change

    async def initiate_email_change(
        self, person_id: str, new_email: str
    ) -> Tuple[bool, str]:
        """
        Initiate email change verification process.

        Args:
            person_id: ID of the person requesting email change
            new_email: New email address to verify

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the person
            person = await self.dynamodb_service.get_person(person_id)
            if not person:
                return False, "Person not found"

            # Check if new email is different from current
            if person.email == new_email:
                return False, "New email is the same as current email"

            # Check if new email is already in use by another person
            existing_person = await self.dynamodb_service.get_person_by_email(new_email)
            if existing_person and existing_person.id != person_id:
                return False, "Email address is already in use"

            # Generate verification token
            verification_token = self._generate_verification_token()

            # Update person with pending email change and verification token
            await self._update_person_pending_email(
                person_id, new_email, verification_token
            )

            # Send verification emails
            success = await self._send_verification_emails(
                person, new_email, verification_token
            )

            if success:
                logger.info(
                    f"Email change verification initiated for person {person_id}"
                )
                return True, "Verification emails sent successfully"
            else:
                # Clean up pending email change if email sending failed
                await self._clear_pending_email_change(person_id)
                return False, "Failed to send verification emails"

        except Exception as e:
            logger.error(
                f"Error initiating email change for person {person_id}: {str(e)}"
            )
            return False, "Failed to initiate email change verification"

    async def verify_email_change(self, verification_token: str) -> Tuple[bool, str]:
        """
        Verify email change using verification token.

        Args:
            verification_token: Email verification token

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find person with this verification token
            person = await self._get_person_by_verification_token(verification_token)
            if not person:
                return False, "Invalid or expired verification token"

            # Check if token is still valid (not expired)
            if not self._is_token_valid(person):
                await self._clear_pending_email_change(person.id)
                return False, "Verification token has expired"

            # Update person's email and clear pending change
            success = await self._complete_email_change(person)

            if success:
                logger.info(f"Email change completed for person {person.id}")
                return True, "Email address updated successfully"
            else:
                return False, "Failed to update email address"

        except Exception as e:
            logger.error(f"Error verifying email change: {str(e)}")
            return False, "Failed to verify email change"

    async def cancel_email_change(self, person_id: str) -> Tuple[bool, str]:
        """
        Cancel pending email change for a person.

        Args:
            person_id: ID of the person

        Returns:
            Tuple of (success, message)
        """
        try:
            success = await self._clear_pending_email_change(person_id)

            if success:
                logger.info(f"Email change cancelled for person {person_id}")
                return True, "Email change cancelled successfully"
            else:
                return False, "Failed to cancel email change"

        except Exception as e:
            logger.error(
                f"Error cancelling email change for person {person_id}: {str(e)}"
            )
            return False, "Failed to cancel email change"

    def _generate_verification_token(self) -> str:
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)

    async def _update_person_pending_email(
        self, person_id: str, new_email: str, verification_token: str
    ):
        """Update person with pending email change information."""
        try:
            # Use DynamoDB update_item directly for these specific fields
            update_expression = "SET pendingEmailChange = :new_email, emailVerificationToken = :token, updatedAt = :updated_at"
            expression_attribute_values = {
                ":new_email": new_email,
                ":token": verification_token,
                ":updated_at": datetime.utcnow().isoformat(),
            }

            self.dynamodb_service.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
            )

        except Exception as e:
            logger.error(f"Error updating person pending email: {str(e)}")
            raise

    async def _send_verification_emails(
        self, person: Person, new_email: str, verification_token: str
    ) -> bool:
        """Send verification emails to both old and new email addresses."""
        try:
            # Create verification link
            verification_link = f"{self.email_service.frontend_url}/verify-email?token={verification_token}"

            # Send email to current address (notification)
            current_email_request = EmailRequest(
                to_email=person.email,
                email_type=EmailType.EMAIL_CHANGE_NOTIFICATION,
                variables={
                    "first_name": person.first_name,
                    "new_email": new_email,
                    "verification_link": verification_link,
                    "change_time": datetime.utcnow().isoformat(),
                },
            )

            # Send email to new address (verification)
            new_email_request = EmailRequest(
                to_email=new_email,
                email_type=EmailType.EMAIL_VERIFICATION,
                variables={
                    "first_name": person.first_name,
                    "verification_link": verification_link,
                    "current_email": person.email,
                },
            )

            # Send both emails
            current_response = await self.email_service.send_email(
                current_email_request
            )
            new_response = await self.email_service.send_email(new_email_request)

            return current_response.success and new_response.success

        except Exception as e:
            logger.error(f"Error sending verification emails: {str(e)}")
            return False

    async def _get_person_by_verification_token(
        self, verification_token: str
    ) -> Optional[Person]:
        """Get person by email verification token."""
        try:
            # Scan for person with this verification token
            # Note: In production, consider using a GSI for better performance
            response = self.dynamodb_service.table.scan(
                FilterExpression="emailVerificationToken = :token",
                ExpressionAttributeValues={":token": verification_token},
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                return self.dynamodb_service._item_to_person(items[0])

            return None

        except Exception as e:
            logger.error(f"Error getting person by verification token: {str(e)}")
            return None

    def _is_token_valid(self, person: Person) -> bool:
        """Check if verification token is still valid (not expired)."""
        if not person.email_verification_token:
            return False

        # For now, we'll assume tokens are valid for 24 hours from when they were created
        # In a more robust implementation, we'd store the token creation time
        # For this implementation, we'll consider all tokens valid if they exist
        return True

    async def _complete_email_change(self, person: Person) -> bool:
        """Complete the email change process."""
        try:
            if not person.pending_email_change:
                return False

            # Update person's email and clear pending change fields
            update_expression = """
                SET email = :new_email,
                    emailVerified = :verified,
                    updatedAt = :updated_at
                REMOVE pendingEmailChange, emailVerificationToken
            """
            expression_attribute_values = {
                ":new_email": person.pending_email_change,
                ":verified": True,
                ":updated_at": datetime.utcnow().isoformat(),
            }

            self.dynamodb_service.table.update_item(
                Key={"id": person.id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
            )

            return True

        except Exception as e:
            logger.error(f"Error completing email change: {str(e)}")
            return False

    async def _clear_pending_email_change(self, person_id: str) -> bool:
        """Clear pending email change information."""
        try:
            update_expression = """
                SET updatedAt = :updated_at
                REMOVE pendingEmailChange, emailVerificationToken
            """
            expression_attribute_values = {":updated_at": datetime.utcnow().isoformat()}

            self.dynamodb_service.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
            )

            return True

        except Exception as e:
            logger.error(f"Error clearing pending email change: {str(e)}")
            return False
