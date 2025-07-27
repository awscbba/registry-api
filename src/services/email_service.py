"""
AWS SES Email Service for sending notifications and password reset emails.
"""
import logging
import os
import json
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from ..models.email import (
    EmailRequest,
    EmailResponse,
    EmailType,
    EmailConfig,
    EMAIL_TEMPLATES
)
from .email_templates import EmailTemplates

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via AWS SES."""

    def __init__(self):
        self.ses_client = boto3.client('ses')
        self.from_email = EmailConfig.get_from_email()
        self.from_name = EmailConfig.DEFAULT_FROM_NAME
        self.configuration_set = os.environ.get('SES_CONFIGURATION_SET')
        self.frontend_url = EmailConfig.get_frontend_url()

    async def send_email(self, request: EmailRequest) -> EmailResponse:
        """
        Send an email using AWS SES.

        Args:
            request: Email request with recipient and template data

        Returns:
            EmailResponse with success status and message ID
        """
        try:
            # Get email template
            template_data = self._prepare_template_data(request)
            template = EmailTemplates.get_template(request.email_type, template_data)

            # Get email configuration
            email_config = EMAIL_TEMPLATES.get(request.email_type)
            if not email_config:
                raise ValueError(f"Email configuration not found for type: {request.email_type}")

            # Prepare SES email parameters
            destination = {
                'ToAddresses': [request.to_email]
            }

            message = {
                'Subject': {
                    'Data': email_config['subject'],
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': template['html_body'],
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': template['text_body'],
                        'Charset': 'UTF-8'
                    }
                }
            }

            # Prepare source email
            source_email = f"{request.from_name or self.from_name} <{self.from_email}>"

            # Prepare SES send parameters
            send_params = {
                'Source': source_email,
                'Destination': destination,
                'Message': message
            }

            # Add configuration set if available
            if self.configuration_set:
                send_params['ConfigurationSetName'] = self.configuration_set

            # Add reply-to if specified
            if request.reply_to:
                send_params['ReplyToAddresses'] = [request.reply_to]

            # Send email via SES
            response = self.ses_client.send_email(**send_params)

            message_id = response.get('MessageId')

            logger.info(f"Email sent successfully: {message_id} to {request.to_email}")

            return EmailResponse(
                success=True,
                message_id=message_id,
                message="Email sent successfully"
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            logger.error(f"SES ClientError: {error_code} - {error_message}")

            return EmailResponse(
                success=False,
                message=f"Failed to send email: {error_message}",
                error_code=error_code
            )

        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")

            return EmailResponse(
                success=False,
                message=f"Failed to send email: {str(e)}"
            )

    async def send_password_reset_email(
        self,
        to_email: str,
        first_name: str,
        reset_token: str
    ) -> EmailResponse:
        """
        Send password reset email with secure reset link.

        Args:
            to_email: Recipient email address
            first_name: Recipient's first name
            reset_token: Password reset token

        Returns:
            EmailResponse with send result
        """
        reset_link = f"{self.frontend_url}/reset-password?token={reset_token}"

        request = EmailRequest(
            to_email=to_email,
            email_type=EmailType.PASSWORD_RESET,
            variables={
                'first_name': first_name,
                'reset_link': reset_link,
                'reset_token': reset_token
            }
        )

        return await self.send_email(request)

    async def send_password_changed_email(
        self,
        to_email: str,
        first_name: str,
        change_time: str,
        ip_address: Optional[str] = None
    ) -> EmailResponse:
        """
        Send password changed confirmation email.

        Args:
            to_email: Recipient email address
            first_name: Recipient's first name
            change_time: When password was changed
            ip_address: IP address of the change

        Returns:
            EmailResponse with send result
        """
        request = EmailRequest(
            to_email=to_email,
            email_type=EmailType.PASSWORD_CHANGED,
            variables={
                'first_name': first_name,
                'change_time': change_time,
                'ip_address': ip_address or 'Not available'
            }
        )

        return await self.send_email(request)

    async def send_password_reset_confirmation_email(
        self,
        to_email: str,
        first_name: str
    ) -> EmailResponse:
        """
        Send password reset confirmation email.

        Args:
            to_email: Recipient email address
            first_name: Recipient's first name

        Returns:
            EmailResponse with send result
        """
        request = EmailRequest(
            to_email=to_email,
            email_type=EmailType.PASSWORD_RESET_CONFIRMATION,
            variables={
                'first_name': first_name
            }
        )

        return await self.send_email(request)

    def _prepare_template_data(self, request: EmailRequest) -> Dict[str, Any]:
        """
        Prepare template data with default values and user variables.

        Args:
            request: Email request with variables

        Returns:
            Dictionary with template data
        """
        # Start with default data
        template_data = {
            'support_email': EmailConfig.DEFAULT_SUPPORT_EMAIL,
            'frontend_url': self.frontend_url,
            'expiry_hours': 1  # Default for password reset
        }

        # Add user-provided variables
        template_data.update(request.variables)

        return template_data

    async def get_send_quota(self) -> Dict[str, Any]:
        """
        Get SES sending quota and statistics.

        Returns:
            Dictionary with quota information
        """
        try:
            quota_response = self.ses_client.get_send_quota()
            stats_response = self.ses_client.get_send_statistics()

            return {
                'max_24_hour_send': quota_response.get('Max24HourSend', 0),
                'max_send_rate': quota_response.get('MaxSendRate', 0),
                'sent_last_24_hours': quota_response.get('SentLast24Hours', 0),
                'send_data_points': stats_response.get('SendDataPoints', [])
            }

        except ClientError as e:
            logger.error(f"Error getting SES quota: {e}")
            return {}

    async def verify_email_identity(self, email: str) -> bool:
        """
        Verify an email identity in SES.

        Args:
            email: Email address to verify

        Returns:
            True if verification was initiated successfully
        """
        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Email verification initiated for: {email}")
            return True

        except ClientError as e:
            logger.error(f"Error verifying email identity: {e}")
            return False
