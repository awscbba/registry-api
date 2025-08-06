"""
Test subscription email notification functionality.

This test verifies that email notifications are sent when subscription status changes.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.email_service import EmailService, EmailType
from src.models.email import EmailResponse


class TestSubscriptionEmailNotifications:
    """Test subscription email notification functionality."""

    @pytest.fixture
    def email_service(self):
        """Create email service instance for testing."""
        return EmailService()

    @pytest.mark.asyncio
    async def test_send_subscription_approved_email(self, email_service):
        """Test sending subscription approval email."""
        # Mock the SES client
        with patch.object(email_service, "ses_client") as mock_ses:
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}

            # Test data
            email = "test@example.com"
            first_name = "Juan"
            last_name = "Pérez"
            project_name = "AWS Workshop 2025"
            project_description = "Taller práctico de AWS"

            # Send approval email
            response = await email_service.send_subscription_approved_email(
                email=email,
                first_name=first_name,
                last_name=last_name,
                project_name=project_name,
                project_description=project_description,
            )

            # Verify response
            assert response.success is True
            assert response.message_id == "test-message-id"
            assert "Email sent successfully" in response.message

            # Verify SES was called
            mock_ses.send_email.assert_called_once()
            call_args = mock_ses.send_email.call_args[1]

            # Verify email content
            assert call_args["Destination"]["ToAddresses"] == [email]
            assert project_name in call_args["Message"]["Subject"]["Data"]
            assert "¡Suscripción Aprobada!" in call_args["Message"]["Subject"]["Data"]
            assert first_name in call_args["Message"]["Body"]["Html"]["Data"]
            assert project_name in call_args["Message"]["Body"]["Html"]["Data"]

    @pytest.mark.asyncio
    async def test_send_subscription_rejected_email(self, email_service):
        """Test sending subscription rejection email."""
        # Mock the SES client
        with patch.object(email_service, "ses_client") as mock_ses:
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}

            # Test data
            email = "test@example.com"
            first_name = "María"
            last_name = "González"
            project_name = "AWS Workshop 2025"
            rejection_reason = "Cupos completos"

            # Send rejection email
            response = await email_service.send_subscription_rejected_email(
                email=email,
                first_name=first_name,
                last_name=last_name,
                project_name=project_name,
                rejection_reason=rejection_reason,
            )

            # Verify response
            assert response.success is True
            assert response.message_id == "test-message-id"
            assert "Email sent successfully" in response.message

            # Verify SES was called
            mock_ses.send_email.assert_called_once()
            call_args = mock_ses.send_email.call_args[1]

            # Verify email content
            assert call_args["Destination"]["ToAddresses"] == [email]
            assert project_name in call_args["Message"]["Subject"]["Data"]
            assert (
                "Actualización de Suscripción"
                in call_args["Message"]["Subject"]["Data"]
            )
            assert first_name in call_args["Message"]["Body"]["Html"]["Data"]
            assert rejection_reason in call_args["Message"]["Body"]["Html"]["Data"]

    @pytest.mark.asyncio
    async def test_email_service_handles_ses_errors(self, email_service):
        """Test that email service handles SES errors gracefully."""
        # Mock SES to raise an exception
        with patch.object(email_service, "ses_client") as mock_ses:
            mock_ses.send_email.side_effect = Exception("SES Error")

            # Try to send approval email
            response = await email_service.send_subscription_approved_email(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                project_name="Test Project",
            )

            # Verify error handling
            assert response.success is False
            assert "SES Error" in response.message
            assert response.error_code == "UNKNOWN_ERROR"

    def test_email_types_include_subscription_notifications(self):
        """Test that EmailType enum includes subscription notification types."""
        # Verify new email types exist
        assert hasattr(EmailType, "SUBSCRIPTION_APPROVED")
        assert hasattr(EmailType, "SUBSCRIPTION_REJECTED")

        # Verify values
        assert EmailType.SUBSCRIPTION_APPROVED == "subscription_approved"
        assert EmailType.SUBSCRIPTION_REJECTED == "subscription_rejected"

    @pytest.mark.asyncio
    async def test_subscription_approved_email_content_structure(self, email_service):
        """Test that approval email has proper content structure."""
        with patch.object(email_service, "ses_client") as mock_ses:
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}

            await email_service.send_subscription_approved_email(
                email="test@example.com",
                first_name="Carlos",
                last_name="Mendoza",
                project_name="DevOps con AWS",
                project_description="Curso completo de DevOps",
            )

            call_args = mock_ses.send_email.call_args[1]
            html_body = call_args["Message"]["Body"]["Html"]["Data"]
            text_body = call_args["Message"]["Body"]["Text"]["Data"]

            # Check HTML content structure
            assert "¡Felicitaciones!" in html_body
            assert "Carlos" in html_body
            assert "DevOps con AWS" in html_body
            assert "Curso completo de DevOps" in html_body
            assert "Acceder al Dashboard" in html_body
            assert "AWS User Group Cochabamba" in html_body

            # Check text content structure
            assert "¡Felicitaciones!" in text_body
            assert "Carlos" in text_body
            assert "DevOps con AWS" in text_body
            assert "Curso completo de DevOps" in text_body

    @pytest.mark.asyncio
    async def test_subscription_rejected_email_content_structure(self, email_service):
        """Test that rejection email has proper content structure."""
        with patch.object(email_service, "ses_client") as mock_ses:
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}

            await email_service.send_subscription_rejected_email(
                email="test@example.com",
                first_name="Ana",
                last_name="Torres",
                project_name="Machine Learning Workshop",
                rejection_reason="Requisitos no cumplidos",
            )

            call_args = mock_ses.send_email.call_args[1]
            html_body = call_args["Message"]["Body"]["Html"]["Data"]
            text_body = call_args["Message"]["Body"]["Text"]["Data"]

            # Check HTML content structure
            assert "Actualización de Suscripción" in html_body
            assert "Ana" in html_body
            assert "Machine Learning Workshop" in html_body
            assert "Requisitos no cumplidos" in html_body
            assert "Contactar Soporte" in html_body
            assert "AWS User Group Cochabamba" in html_body

            # Check text content structure
            assert "Actualización de Suscripción" in text_body
            assert "Ana" in text_body
            assert "Machine Learning Workshop" in text_body
            assert "Requisitos no cumplidos" in text_body
