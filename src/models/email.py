"""
Email service models for AWS SES integration.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class EmailType(str, Enum):
    """Types of emails that can be sent."""
    PASSWORD_RESET = "password_reset"
    PASSWORD_RESET_CONFIRMATION = "password_reset_confirmation"
    PASSWORD_CHANGED = "password_changed"
    ADMIN_PASSWORD_RESET = "admin_password_reset"
    SECURITY_ALERT = "security_alert"
    WELCOME = "welcome"
    ACCOUNT_LOCKED = "account_locked"
    EMAIL_VERIFICATION = "email_verification"
    EMAIL_CHANGE_NOTIFICATION = "email_change_notification"


class EmailTemplate(BaseModel):
    """Email template model."""

    template_name: str = Field(..., description="Template identifier")
    subject: str = Field(..., description="Email subject line")
    html_body: str = Field(..., description="HTML email body")
    text_body: str = Field(..., description="Plain text email body")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")


class EmailRequest(BaseModel):
    """Email sending request model."""

    to_email: EmailStr = Field(..., description="Recipient email address")
    email_type: EmailType = Field(..., description="Type of email to send")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    from_name: Optional[str] = Field(None, description="Sender name")
    reply_to: Optional[EmailStr] = Field(None, description="Reply-to email address")


class EmailResponse(BaseModel):
    """Email sending response model."""

    success: bool = Field(..., description="Whether email was sent successfully")
    message_id: Optional[str] = Field(None, description="SES message ID")
    message: str = Field(..., description="Response message")
    error_code: Optional[str] = Field(None, description="Error code if failed")


class EmailDeliveryStatus(BaseModel):
    """Email delivery status tracking."""

    message_id: str = Field(..., description="SES message ID")
    email: EmailStr = Field(..., description="Recipient email")
    status: str = Field(..., description="Delivery status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bounce_reason: Optional[str] = Field(None, description="Bounce reason if applicable")
    complaint_reason: Optional[str] = Field(None, description="Complaint reason if applicable")


class PasswordResetEmailData(BaseModel):
    """Data for password reset email template."""

    first_name: str = Field(..., description="Recipient's first name")
    reset_link: str = Field(..., description="Password reset link")
    expiry_hours: int = Field(default=1, description="Link expiry in hours")
    support_email: str = Field(default="support@people-register.local", description="Support email")


class PasswordChangedEmailData(BaseModel):
    """Data for password changed confirmation email."""

    first_name: str = Field(..., description="Recipient's first name")
    change_time: datetime = Field(..., description="When password was changed")
    ip_address: Optional[str] = Field(None, description="IP address of change")
    support_email: str = Field(default="support@people-register.local", description="Support email")


class SecurityAlertEmailData(BaseModel):
    """Data for security alert email."""

    first_name: str = Field(..., description="Recipient's first name")
    alert_type: str = Field(..., description="Type of security alert")
    alert_time: datetime = Field(..., description="When alert occurred")
    ip_address: Optional[str] = Field(None, description="IP address involved")
    location: Optional[str] = Field(None, description="Approximate location")
    support_email: str = Field(default="support@people-register.local", description="Support email")


class WelcomeEmailData(BaseModel):
    """Data for welcome email template."""

    first_name: str = Field(..., description="Recipient's first name")
    login_url: str = Field(..., description="Login URL")
    temporary_password: Optional[str] = Field(None, description="Temporary password if applicable")
    support_email: str = Field(default="support@people-register.local", description="Support email")


# Email template configurations
EMAIL_TEMPLATES = {
    EmailType.PASSWORD_RESET: {
        "subject": "Reset Your Password - People Register",
        "template_name": "password_reset"
    },
    EmailType.PASSWORD_RESET_CONFIRMATION: {
        "subject": "Password Reset Successful - People Register",
        "template_name": "password_reset_confirmation"
    },
    EmailType.PASSWORD_CHANGED: {
        "subject": "Password Changed - People Register",
        "template_name": "password_changed"
    },
    EmailType.ADMIN_PASSWORD_RESET: {
        "subject": "Your Password Has Been Reset - People Register",
        "template_name": "admin_password_reset"
    },
    EmailType.SECURITY_ALERT: {
        "subject": "Security Alert - People Register",
        "template_name": "security_alert"
    },
    EmailType.WELCOME: {
        "subject": "Welcome to People Register",
        "template_name": "welcome"
    },
    EmailType.ACCOUNT_LOCKED: {
        "subject": "Account Security Alert - People Register",
        "template_name": "account_locked"
    },
    EmailType.EMAIL_VERIFICATION: {
        "subject": "Verify Your New Email Address - People Register",
        "template_name": "email_verification"
    },
    EmailType.EMAIL_CHANGE_NOTIFICATION: {
        "subject": "Email Change Request - People Register",
        "template_name": "email_change_notification"
    }
}


class EmailConfig:
    """Email service configuration."""

    # Default sender information
    DEFAULT_FROM_NAME = "People Register"
    DEFAULT_SUPPORT_EMAIL = "support@people-register.local"

    # Email template settings
    TEMPLATE_CACHE_TTL = 3600  # 1 hour

    # SES settings
    MAX_SEND_RATE = 14  # SES default for new accounts
    MAX_SEND_QUOTA = 200  # SES default for new accounts

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    @classmethod
    def get_frontend_url(cls) -> str:
        """Get frontend URL from environment or default."""
        import os
        return os.environ.get('FRONTEND_URL', 'https://d28z2il3z2vmpc.cloudfront.net')

    @classmethod
    def get_from_email(cls) -> str:
        """Get from email from environment or default."""
        import os
        return os.environ.get('SES_FROM_EMAIL', 'noreply@people-register.local')
