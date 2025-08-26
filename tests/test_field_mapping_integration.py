"""
Integration tests for field mapping in database operations.

These tests ensure that field updates actually persist to the database
and would have caught the missing field mapping bug.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.handlers.modular_api_handler import app
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService
from src.models.person import PersonUpdate, Address


@pytest.mark.skip(
    reason="Integration test needs proper test database setup and address field handling"
)
class TestFieldMappingIntegration:
    """Test that field updates actually persist to the database."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_person_phone_field_mapping_integration(self):
        """
        CRITICAL: Test that phone field updates actually persist to database.

        This test would have caught the missing 'phone' field mapping bug.
        """
        # Use real database service (not mocked)
        db_service = DefensiveDynamoDBService()

        # Create a test person first
        from src.models.person import PersonCreate

        test_person = PersonCreate(
            firstName="Test",
            lastName="User",
            email="test.phone@example.com",
            phone="555-0000",
            dateOfBirth="1990-01-01",
        )

        # Create person in database
        created_person = await db_service.create_person(test_person)
        assert created_person is not None
        person_id = created_person.id

        try:
            # Update ONLY the phone field
            update_data = PersonUpdate(phone="555-9999")
            updated_person = await db_service.update_person(person_id, update_data)

            # CRITICAL: Verify the phone was actually updated
            assert updated_person is not None, "Update should return updated person"
            assert (
                updated_person.phone == "555-9999"
            ), f"Phone should be updated to 555-9999, got {updated_person.phone}"

            # DOUBLE CHECK: Retrieve from database again
            retrieved_person = await db_service.get_person(person_id)
            assert retrieved_person is not None, "Should be able to retrieve person"
            assert (
                retrieved_person.phone == "555-9999"
            ), f"Phone should persist in database, got {retrieved_person.phone}"

        finally:
            # Cleanup
            await db_service.delete_person(person_id)

    @pytest.mark.asyncio
    async def test_person_email_field_mapping_integration(self):
        """Test that email field updates actually persist to database."""
        db_service = DefensiveDynamoDBService()

        from src.models.person import PersonCreate

        test_person = PersonCreate(
            firstName="Test",
            lastName="User",
            email="test.email@example.com",
            phone="555-0000",
            dateOfBirth="1990-01-01",
        )

        created_person = await db_service.create_person(test_person)
        person_id = created_person.id

        try:
            # Update ONLY the email field
            update_data = PersonUpdate(email="updated.email@example.com")
            updated_person = await db_service.update_person(person_id, update_data)

            # CRITICAL: Verify the email was actually updated
            assert updated_person.email == "updated.email@example.com"

            # DOUBLE CHECK: Retrieve from database
            retrieved_person = await db_service.get_person(person_id)
            assert retrieved_person.email == "updated.email@example.com"

        finally:
            await db_service.delete_person(person_id)

    @pytest.mark.asyncio
    async def test_project_field_mapping_integration(self):
        """Test that project field updates actually persist to database."""
        db_service = DefensiveDynamoDBService()

        from src.models.project import ProjectCreate

        test_project = ProjectCreate(
            name="Test Project",
            description="Original description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=10,
        )

        created_project = await db_service.create_project(test_project)
        project_id = created_project.id

        try:
            # Update multiple fields
            from src.models.project import ProjectUpdate

            update_data = ProjectUpdate(
                name="Updated Project Name",
                description="Updated description",
                maxParticipants=20,
            )

            updated_project = await db_service.update_project(project_id, update_data)

            # CRITICAL: Verify all fields were actually updated
            assert updated_project.name == "Updated Project Name"
            assert updated_project.description == "Updated description"
            assert updated_project.maxParticipants == 20

            # DOUBLE CHECK: Retrieve from database
            retrieved_project = await db_service.get_project_by_id(project_id)
            assert retrieved_project.name == "Updated Project Name"
            assert retrieved_project.description == "Updated description"
            assert retrieved_project.maxParticipants == 20

        finally:
            await db_service.delete_project(project_id)

    def test_api_endpoint_field_persistence_integration(self, client):
        """
        Test that API endpoints actually persist field updates to database.

        This is an end-to-end test that would catch field mapping issues.
        """
        # Mock authentication
        with patch("src.handlers.modular_api_handler.get_current_user") as mock_auth:
            mock_auth.return_value = {
                "id": "admin-user-id",
                "email": "admin@example.com",
                "isAdmin": True,
            }

            # Create a person via API
            create_data = {
                "firstName": "API",
                "lastName": "Test",
                "email": "api.test@example.com",
                "phone": "555-1111",
                "dateOfBirth": "1990-01-01",
            }

            response = client.post("/v2/people", json=create_data)
            assert response.status_code == 201

            person_data = response.json()["data"]
            person_id = person_data["id"]

            try:
                # Update phone via API
                update_data = {"phone": "555-2222"}
                response = client.put(f"/v2/people/{person_id}", json=update_data)
                assert response.status_code == 200

                # CRITICAL: Retrieve via API and verify persistence
                response = client.get(f"/v2/people/{person_id}")
                assert response.status_code == 200

                retrieved_data = response.json()["data"]
                assert (
                    retrieved_data["phone"] == "555-2222"
                ), f"Phone should be updated, got {retrieved_data.get('phone')}"

            finally:
                # Cleanup
                client.delete(f"/v2/people/{person_id}")
