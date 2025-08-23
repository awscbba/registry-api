"""
Tests for routing fix to ensure all subscription endpoints use v2 logic with password generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.person import Person


@pytest.mark.skip(reason="Temporarily skipped - uses deprecated versioned_api_handler")
class TestRoutingFix:
    """Test that all subscription endpoints now use v2 logic with password generation."""

    @pytest.mark.asyncio
    async def test_legacy_endpoint_redirects_to_v2(self):
        """Test that /public/subscribe (legacy) now uses v2 logic."""
        # Arrange
        mock_db_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Mock no existing person
        mock_db_service.get_person_by_email.return_value = None

        # Mock project exists and is active
        mock_db_service.get_project_by_id.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "maxParticipants": 10,
            "status": "active",
        }
        mock_db_service.get_subscriptions_by_project.return_value = []

        # Mock person creation
        created_person = Person(
            id="person-123",
            firstName="Legacy",
            lastName="Test",
            email="legacy@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "123 Legacy St",
                "city": "Legacy City",
                "state": "Legacy State",
                "postalCode": "12345",
                "country": "Legacy Country",
            },
            isAdmin=False,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
        )
        mock_db_service.create_person.return_value = created_person

        # Mock subscription creation
        mock_db_service.create_subscription.return_value = {
            "id": "sub-123",
            "projectId": "project-123",
            "personId": "person-123",
            "status": "pending",
        }

        # Mock email service
        mock_email_service.generate_temporary_password = MagicMock(
            return_value="LegacyPass123!"
        )
        mock_email_service.send_welcome_email = AsyncMock(
            return_value=MagicMock(success=True)
        )

        # Act
        with (
            patch("src.handlers.versioned_api_handler.db_service", mock_db_service),
            patch(
                "src.handlers.versioned_api_handler.email_service", mock_email_service
            ),
        ):
            from src.handlers.versioned_api_handler import create_subscription_legacy

            subscription_data = {
                "person": {
                    "firstName": "Legacy",
                    "lastName": "Test",
                    "email": "legacy@example.com",
                    "phone": "1234567890",
                },
                "projectId": "project-123",
                "notes": "Testing legacy endpoint redirect",
            }

            result = await create_subscription_legacy(subscription_data)

        # Assert - Should have v2 features
        assert result["person_created"] is True
        assert result["temporary_password_generated"] is True
        assert result["email_sent"] is True
        assert result["version"] == "v2"  # Should be v2, not legacy
        assert "credenciales de acceso" in result["message"]  # Spanish message from v2

        # Verify password generation was called
        mock_email_service.generate_temporary_password.assert_called_once()
        mock_email_service.send_welcome_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_v1_endpoint_redirects_to_v2_with_deprecation_notice(self):
        """Test that /v1/public/subscribe now uses v2 logic with deprecation notice."""
        # Arrange
        mock_db_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Mock no existing person
        mock_db_service.get_person_by_email.return_value = None

        # Mock project exists and is active
        mock_db_service.get_project_by_id.return_value = {
            "id": "project-456",
            "name": "V1 Test Project",
            "maxParticipants": 10,
            "status": "active",
        }
        mock_db_service.get_subscriptions_by_project.return_value = []

        # Mock person creation
        created_person = Person(
            id="person-456",
            firstName="V1",
            lastName="Test",
            email="v1@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "123 V1 St",
                "city": "V1 City",
                "state": "V1 State",
                "postalCode": "12345",
                "country": "V1 Country",
            },
            isAdmin=False,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
        )
        mock_db_service.create_person.return_value = created_person

        # Mock subscription creation
        mock_db_service.create_subscription.return_value = {
            "id": "sub-456",
            "projectId": "project-456",
            "personId": "person-456",
            "status": "pending",
        }

        # Mock email service
        mock_email_service.generate_temporary_password = MagicMock(
            return_value="V1Pass456!"
        )
        mock_email_service.send_welcome_email = AsyncMock(
            return_value=MagicMock(success=True)
        )

        # Act
        with (
            patch("src.handlers.versioned_api_handler.db_service", mock_db_service),
            patch(
                "src.handlers.versioned_api_handler.email_service", mock_email_service
            ),
        ):
            from src.handlers.versioned_api_handler import create_subscription_v1

            subscription_data = {
                "person": {
                    "firstName": "V1",
                    "lastName": "Test",
                    "email": "v1@example.com",
                    "phone": "1234567890",
                },
                "projectId": "project-456",
                "notes": "Testing v1 endpoint redirect",
            }

            result = await create_subscription_v1(subscription_data)

        # Assert - Should have v2 features with deprecation notice
        assert result["person_created"] is True
        assert result["temporary_password_generated"] is True
        assert result["email_sent"] is True
        assert result["deprecated"] is True  # Deprecation flag
        assert result["version"] == "v1-redirected-to-v2"  # Special version indicator
        assert "DEPRECATED" in result["message"]  # Deprecation notice in message
        assert "/v2/public/subscribe" in result["message"]  # Recommendation to use v2

        # Verify password generation was called
        mock_email_service.generate_temporary_password.assert_called_once()
        mock_email_service.send_welcome_email.assert_called_once()

    def test_routing_fix_prevents_password_bug(self):
        """Test that routing fix prevents the original password bug."""
        # This test ensures that all endpoints now use PersonCreate models
        # with password fields, preventing the original bug

        from src.handlers.versioned_api_handler import (
            create_subscription_legacy,
            create_subscription_v1,
        )
        from src.models.person import PersonCreate

        # Verify PersonCreate has password fields (the original bug fix)
        person_fields = PersonCreate.model_fields.keys()
        assert (
            "password_hash" in person_fields
        ), "PersonCreate must have password_hash field"
        assert (
            "password_salt" in person_fields
        ), "PersonCreate must have password_salt field"

        # Verify functions exist and are callable
        assert callable(create_subscription_legacy), "Legacy endpoint must be callable"
        assert callable(create_subscription_v1), "V1 endpoint must be callable"

        # Verify docstrings indicate v2 redirect
        assert "redirects to v2" in create_subscription_legacy.__doc__.lower()
        assert "redirects to v2" in create_subscription_v1.__doc__.lower()


if __name__ == "__main__":
    pytest.main([__file__])
