"""Tests for Email Service - Critical service with 0% coverage"""

import pytest
from unittest.mock import Mock, patch
from src.services.email_service import EmailService
from src.exceptions.base_exceptions import BusinessLogicException as EmailException


class TestEmailService:
    """Test Email Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.email_service = EmailService()

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email sending"""
        # Arrange
        to_email = "user@example.com"
        subject = "Test Subject"
        body = "Test email body"

        with patch("boto3.client") as mock_boto3:
            mock_ses = Mock()
            mock_boto3.return_value = mock_ses
            mock_ses.send_email.return_value = {"MessageId": "msg123"}

            # Act
            result = await self.email_service.send_email(to_email, subject, body)

            # Assert
            assert result["success"] is True
            assert result["message_id"] == "msg123"
            mock_ses.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_failure(self):
        """Test email sending failure"""
        # Arrange
        to_email = "user@example.com"
        subject = "Test Subject"
        body = "Test email body"

        with patch("boto3.client") as mock_boto3:
            mock_ses = Mock()
            mock_boto3.return_value = mock_ses
            mock_ses.send_email.side_effect = Exception("SES Error")

            # Act & Assert
            with pytest.raises(EmailException):
                await self.email_service.send_email(to_email, subject, body)

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self):
        """Test sending password reset email"""
        # Arrange
        to_email = "user@example.com"
        reset_token = "reset123"
        user_name = "John Doe"

        with patch.object(self.email_service, "send_email") as mock_send:
            mock_send.return_value = {"success": True, "message_id": "msg123"}

            # Act
            result = await self.email_service.send_password_reset_email(
                to_email, reset_token, user_name
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify email content
            call_args = mock_send.call_args
            assert to_email in call_args[0]
            assert "Password Reset" in call_args[0][1]  # Subject
            assert reset_token in call_args[0][2]  # Body

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(self):
        """Test sending welcome email"""
        # Arrange
        to_email = "newuser@example.com"
        user_name = "Jane Doe"

        with patch.object(self.email_service, "send_email") as mock_send:
            mock_send.return_value = {"success": True, "message_id": "msg456"}

            # Act
            result = await self.email_service.send_welcome_email(to_email, user_name)

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify email content
            call_args = mock_send.call_args
            assert to_email in call_args[0]
            assert "Welcome" in call_args[0][1]  # Subject
            assert user_name in call_args[0][2]  # Body

    @pytest.mark.asyncio
    async def test_send_notification_email_success(self):
        """Test sending notification email"""
        # Arrange
        to_email = "user@example.com"
        notification_type = "subscription_update"
        data = {"project_name": "Test Project", "status": "active"}

        with patch.object(self.email_service, "send_email") as mock_send:
            mock_send.return_value = {"success": True, "message_id": "msg789"}

            # Act
            result = await self.email_service.send_notification_email(
                to_email, notification_type, data
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

    def test_email_service_initialization(self):
        """Test email service initializes correctly"""
        # Act
        service = EmailService()

        # Assert
        assert hasattr(service, "ses_client")

    @pytest.mark.asyncio
    async def test_validate_email_address_valid(self):
        """Test email address validation - valid"""
        # Arrange
        valid_email = "user@example.com"

        # Act
        result = await self.email_service.validate_email_address(valid_email)

        # Assert
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_email_address_invalid(self):
        """Test email address validation - invalid"""
        # Arrange
        invalid_email = "invalid-email"

        # Act
        result = await self.email_service.validate_email_address(invalid_email)

        # Assert
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_get_email_template_success(self):
        """Test getting email template"""
        # Arrange
        template_name = "password_reset"

        # Act
        result = await self.email_service.get_email_template(template_name)

        # Assert
        assert "subject" in result
        assert "body" in result
        assert isinstance(result["subject"], str)
        assert isinstance(result["body"], str)

    @pytest.mark.asyncio
    async def test_send_bulk_email_success(self):
        """Test sending bulk emails"""
        # Arrange
        recipients = ["user1@example.com", "user2@example.com"]
        subject = "Bulk Email Subject"
        body = "Bulk email body"

        with patch.object(self.email_service, "send_email") as mock_send:
            mock_send.return_value = {"success": True, "message_id": "msg123"}

            # Act
            result = await self.email_service.send_bulk_email(recipients, subject, body)

            # Assert
            assert result["success"] is True
            assert result["sent_count"] == 2
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_email_error_handling(self):
        """Test error handling in email operations"""
        # Arrange
        to_email = "user@example.com"
        subject = "Test"
        body = "Test"

        with patch("boto3.client", side_effect=Exception("AWS Error")):

            # Act & Assert
            with pytest.raises(EmailException):
                await self.email_service.send_email(to_email, subject, body)
