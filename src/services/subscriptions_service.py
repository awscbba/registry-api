"""
Subscriptions Service - Domain service for subscription-related operations.
Implements the Service Registry pattern for subscription management.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from src.core.base_service import BaseService
from src.models.subscription import SubscriptionCreate, SubscriptionUpdate
from src.utils.logging_config import get_handler_logger
from src.utils.error_handler import handle_database_error
from src.utils.response_models import create_v1_response, create_v2_response


class SubscriptionsService(BaseService):
    """Service for managing subscription-related operations."""

    def __init__(self):
        super().__init__("subscriptions_service")
        # Use environment variable for table name
        table_name = os.getenv("SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable")
        # Initialize repository for clean data access
        from src.repositories.subscription_repository import SubscriptionRepository
        from src.repositories.user_repository import UserRepository

        self.subscription_repository = SubscriptionRepository(table_name=table_name)
        self.user_repository = UserRepository()
        self.logger = get_handler_logger("subscriptions_service")

    async def initialize(self):
        """Initialize the subscriptions service with repository pattern."""
        try:
            # Test repository connectivity with a simple count operation
            count_result = await self.subscription_repository.count()
            if count_result.success:
                self.logger.info(
                    f"Subscriptions service initialized successfully. Found {count_result.data} subscriptions."
                )
                return True
            else:
                self.logger.error(
                    f"Repository health check failed: {count_result.error}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize subscriptions service: {str(e)}")
            return False

    async def health_check(self):
        """Check the health of the subscriptions service."""
        from ..core.base_service import HealthCheck, ServiceStatus
        import time

        start_time = time.time()

        try:
            # Use a lightweight health check with timeout
            import asyncio

            # Try a quick database connectivity test with 1 second timeout
            try:
                await asyncio.wait_for(self._quick_db_check(), timeout=1.0)
                response_time = (time.time() - start_time) * 1000
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.HEALTHY,
                    message="Subscriptions service is healthy",
                    details={
                        "database": "connected",
                        "timestamp": datetime.now().isoformat(),
                    },
                    response_time_ms=response_time,
                )
            except asyncio.TimeoutError:
                response_time = (time.time() - start_time) * 1000
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.DEGRADED,
                    message="Database check timed out",
                    details={
                        "database": "timeout",
                        "timestamp": datetime.now().isoformat(),
                    },
                    response_time_ms=response_time,
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Subscriptions service health check failed: {str(e)}")
            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={
                    "database": "disconnected",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                response_time_ms=response_time,
            )

    async def _quick_db_check(self):
        """Quick database connectivity check."""
        # Try to get just one subscription with limit=1 for faster response
        try:
            result = await self.subscription_repository.list_all()
            return result.success
        except Exception:
            # If we can't connect, that's still a valid health check result
            raise

    async def get_all_subscriptions_v1(self) -> Dict[str, Any]:
        """Get all subscriptions (v1 format)."""
        try:
            self.logger.log_api_request("GET", "/v1/subscriptions")
            result = await self.subscription_repository.list_all()

            if not result.success:
                raise Exception(result.error)

            subscriptions = result.data

            response = create_v1_response(subscriptions)
            self.logger.log_api_response("GET", "/v1/subscriptions", 200)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve subscriptions",
                operation="get_all_subscriptions_v1",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving subscriptions", e)

    async def get_all_subscriptions_v2(self) -> Dict[str, Any]:
        """Get all subscriptions (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", "/v2/subscriptions")
            result = await self.subscription_repository.list_all()

            if not result.success:
                raise Exception(result.error)

            subscriptions = result.data

            response = create_v2_response(
                subscriptions,
                metadata={
                    "total_count": len(subscriptions),
                    "service": "subscriptions_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response(
                "GET",
                "/v2/subscriptions",
                200,
                additional_context={"count": len(subscriptions)},
            )
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve subscriptions",
                operation="get_all_subscriptions_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving subscriptions", e)

    async def get_subscription_by_id_v1(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription by ID (v1 format)."""
        try:
            self.logger.log_api_request("GET", f"/v1/subscriptions/{subscription_id}")
            result = await self.subscription_repository.get_by_id(subscription_id)

            if not result.success or not result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            subscription = result.data
            response = create_v1_response(subscription)
            self.logger.log_api_response(
                "GET", f"/v1/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve subscription",
                operation="get_subscription_by_id_v1",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving subscription", e)

    async def get_subscription_by_id_v2(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription by ID (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", f"/v2/subscriptions/{subscription_id}")
            result = await self.subscription_repository.get_by_id(subscription_id)

            if not result.success or not result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            subscription = result.data
            response = create_v2_response(
                subscription,
                metadata={
                    "subscription_id": subscription_id,
                    "service": "subscriptions_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response(
                "GET", f"/v2/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve subscription",
                operation="get_subscription_by_id_v2",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving subscription", e)

    async def create_subscription_v1(self, subscription_data: dict) -> Dict[str, Any]:
        """Create a new subscription (v1 format - redirects to v2 for password generation)."""
        # Redirect to v2 implementation for password generation and bug fixes
        result = await self.create_subscription_v2(subscription_data)

        # Add deprecation notice to response
        if isinstance(result, dict):
            result["deprecated"] = True
            result["message"] = (
                f"{result.get('message', '')} [DEPRECATED: Use /v2/public/subscribe]"
            )
            result["version"] = "v1-redirected-to-v2"

        return result

    async def create_subscription_v2(self, subscription_data: dict) -> Dict[str, Any]:
        """Create a new subscription (v2 format with enhanced features and password generation)."""
        try:
            self.logger.log_api_request("POST", "/v2/public/subscribe")

            # Check if this is a direct subscription creation (with personId/projectId)
            # or a public subscription (with person object and project info)
            if "personId" in subscription_data and "projectId" in subscription_data:
                # Direct subscription creation - use the existing model
                subscription_create = SubscriptionCreate(**subscription_data)

                # Create subscription using repository
                result = await self.subscription_repository.create(subscription_create)

                if not result.success:
                    raise Exception(result.error)

                created_subscription = result.data

                response = create_v2_response(
                    created_subscription,
                    metadata={
                        "subscription_id": (
                            created_subscription.get("id")
                            if isinstance(created_subscription, dict)
                            else getattr(created_subscription, "id", None)
                        ),
                        "service": "subscriptions_service",
                        "version": "v2",
                        "created_at": datetime.now().isoformat(),
                    },
                )
            else:
                # Public subscription - handle person creation workflow
                # This should work like create_project_subscription_v2 but for public subscriptions
                # For now, require projectId to be provided
                if "projectId" not in subscription_data:
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="projectId is required for public subscriptions",
                    )

                project_id = subscription_data["projectId"]
                # Use the project subscription workflow
                response = await self.create_project_subscription_v2(
                    project_id, subscription_data
                )

            self.logger.log_api_response("POST", "/v2/public/subscribe", 201)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to create subscription",
                operation="create_subscription_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating subscription", e)

    async def update_subscription_v1(
        self, subscription_id: str, subscription_data: SubscriptionUpdate
    ) -> Dict[str, Any]:
        """Update subscription (v1 format)."""
        try:
            self.logger.log_api_request("PUT", f"/v1/subscriptions/{subscription_id}")

            # Check if subscription exists
            existing_result = await self.subscription_repository.get_by_id(
                subscription_id
            )
            if not existing_result.success or not existing_result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Update subscription
            result = await self.subscription_repository.update(
                subscription_id, subscription_data
            )

            if not result.success:
                raise Exception(result.error)

            updated_subscription = result.data

            response = create_v1_response(updated_subscription)
            self.logger.log_api_response(
                "PUT", f"/v1/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update subscription",
                operation="update_subscription_v1",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating subscription", e)

    async def update_subscription_v2(
        self, subscription_id: str, subscription_data: SubscriptionUpdate
    ) -> Dict[str, Any]:
        """Update subscription (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("PUT", f"/v2/subscriptions/{subscription_id}")

            # Check if subscription exists
            existing_result = await self.subscription_repository.get_by_id(
                subscription_id
            )
            if not existing_result.success or not existing_result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Get the existing subscription and merge with updates
            existing_subscription = existing_result.data

            # Update only the fields that are provided
            if subscription_data.status is not None:
                existing_subscription.status = subscription_data.status.value
            if subscription_data.notes is not None:
                existing_subscription.notes = subscription_data.notes

            # Update subscription using the full entity
            result = await self.subscription_repository.update(existing_subscription)

            if not result.success:
                raise Exception(result.error)

            updated_subscription = result.data

            response = create_v2_response(
                updated_subscription,
                metadata={
                    "subscription_id": subscription_id,
                    "service": "subscriptions_service",
                    "version": "v2",
                    "updated_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response(
                "PUT", f"/v2/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update subscription",
                operation="update_subscription_v2",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating subscription", e)

    async def delete_subscription_v1(self, subscription_id: str) -> Dict[str, Any]:
        """Delete subscription (v1 format)."""
        try:
            self.logger.log_api_request(
                "DELETE", f"/v1/subscriptions/{subscription_id}"
            )

            # Check if subscription exists
            existing_result = await self.subscription_repository.get_by_id(
                subscription_id
            )
            if not existing_result.success or not existing_result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Delete subscription
            result = await self.subscription_repository.delete(subscription_id)
            if not result.success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete subscription",
                )

            response = create_v1_response(
                {
                    "message": "Subscription deleted successfully",
                    "subscriptionId": subscription_id,
                }
            )
            self.logger.log_api_response(
                "DELETE", f"/v1/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete subscription",
                operation="delete_subscription_v1",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting subscription", e)

    async def delete_subscription_v2(self, subscription_id: str) -> Dict[str, Any]:
        """Delete subscription (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request(
                "DELETE", f"/v2/subscriptions/{subscription_id}"
            )

            # Check if subscription exists
            existing_result = await self.subscription_repository.get_by_id(
                subscription_id
            )
            if not existing_result.success or not existing_result.data:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Delete subscription
            result = await self.subscription_repository.delete(subscription_id)
            if not result.success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete subscription",
                )

            response = create_v2_response(
                {
                    "message": "Subscription deleted successfully",
                    "subscriptionId": subscription_id,
                },
                metadata={
                    "subscription_id": subscription_id,
                    "service": "subscriptions_service",
                    "version": "v2",
                    "deleted_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response(
                "DELETE", f"/v2/subscriptions/{subscription_id}", 200
            )
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete subscription",
                operation="delete_subscription_v2",
                subscription_id=subscription_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting subscription", e)

    async def get_project_subscriptions_v1(self, project_id: str) -> Dict[str, Any]:
        """Get subscriptions for a specific project (v1 format)."""
        try:
            self.logger.log_api_request(
                "GET", f"/v1/projects/{project_id}/subscriptions"
            )
            result = await self.subscription_repository.get_by_project_id(project_id)

            if not result.success:
                raise Exception(result.error)

            subscriptions = result.data

            response = create_v1_response(subscriptions)
            self.logger.log_api_response(
                "GET", f"/v1/projects/{project_id}/subscriptions", 200
            )
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve project subscriptions",
                operation="get_project_subscriptions_v1",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving project subscriptions", e)

    async def get_project_subscriptions_v2(self, project_id: str) -> Dict[str, Any]:
        """Get subscriptions for a specific project (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request(
                "GET", f"/v2/projects/{project_id}/subscriptions"
            )
            result = await self.subscription_repository.get_by_project_id(project_id)

            if not result.success:
                raise Exception(result.error)

            subscriptions = result.data

            response = create_v2_response(
                subscriptions,
                metadata={
                    "project_id": project_id,
                    "total_count": len(subscriptions),
                    "service": "subscriptions_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response(
                "GET",
                f"/v2/projects/{project_id}/subscriptions",
                200,
                additional_context={
                    "project_id": project_id,
                    "count": len(subscriptions),
                },
            )
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve project subscriptions",
                operation="get_project_subscriptions_v2",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving project subscriptions", e)

    async def create_project_subscription_v2(
        self, project_id: str, subscription_data: dict
    ) -> Dict[str, Any]:
        """Create a new subscription for a project (v2 format with email notification)."""
        try:
            self.logger.info(
                "Creating project subscription",
                operation="create_project_subscription_v2",
                project_id=project_id,
                subscription_data=subscription_data,
            )

            # Validate required fields
            if not subscription_data.get("person"):
                self.logger.error("Missing person data in subscription request")
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Person information is required",
                )

            person_data = subscription_data["person"]
            if not person_data.get("email"):
                self.logger.error("Missing person email in subscription request")
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Person email is required",
                )

            # Step 1: Find or create the person using repository pattern
            self.logger.info(f"Looking for person with email: {person_data['email']}")

            # Check if person already exists
            person_result = await self.user_repository.get_by_email(
                person_data["email"]
            )

            if person_result.success and person_result.data:
                self.logger.info(f"Found existing person: {person_result.data.id}")
                person_id = person_result.data.id
            else:
                # Create new person using repository
                self.logger.info("Creating new person")
                from src.models.person import PersonCreate, Address

                # Parse the name into first and last name
                full_name = person_data.get("name", "").strip()
                name_parts = full_name.split(" ", 1) if full_name else ["", ""]
                first_name = name_parts[0] if len(name_parts) > 0 else "Unknown"
                last_name = name_parts[1] if len(name_parts) > 1 else "User"

                # Create a default address
                default_address = Address(
                    street="Not provided",
                    city="Not provided",
                    state="Not provided",
                    postalCode="00000",  # Use the alias field name
                    country="Not provided",
                )

                new_person_data = PersonCreate(
                    firstName=first_name,  # Use alias field name
                    lastName=last_name,  # Use alias field name
                    email=person_data["email"],
                    phone="",  # Optional field
                    dateOfBirth="1900-01-01",  # Use alias field name
                    address=default_address,
                    isAdmin=False,  # Use alias field name
                )

                create_result = await self.user_repository.create(new_person_data)
                if not create_result.success:
                    raise Exception(f"Failed to create person: {create_result.error}")

                person_id = create_result.data.id
                self.logger.info(f"Created new person with ID: {person_id}")

            # Step 2: Create the subscription using repository pattern
            from src.models.subscription import SubscriptionCreate

            subscription_create_data = SubscriptionCreate(
                personId=person_id,
                projectId=project_id,
                status="active",
                notes=subscription_data.get("notes", ""),
            )

            self.logger.info(
                f"Creating subscription using repository: {subscription_create_data}"
            )

            # Use repository for subscription creation
            result = await self.subscription_repository.create(subscription_create_data)

            if not result.success:
                raise Exception(f"Failed to create subscription: {result.error}")

            created_subscription = result.data

            self.logger.info(
                f"Subscription created successfully: {created_subscription}"
            )

            # Enhanced v2 response format
            response = create_v2_response(
                data={
                    "subscription": created_subscription,
                    "email_sent": False,  # TODO: Implement email sending
                    "project_id": project_id,
                    "person_email": person_data["email"],
                    "person_id": person_id,
                    "message": "Subscription created successfully",
                },
            )

            self.logger.info(
                "Project subscription created successfully",
                operation="create_project_subscription_v2",
                project_id=project_id,
                subscription_id=(
                    created_subscription.get("id")
                    if isinstance(created_subscription, dict)
                    else getattr(created_subscription, "id", None)
                ),
                person_id=person_id,
            )
            return response

        except Exception as e:
            self.logger.error(
                "Failed to create project subscription",
                operation="create_project_subscription_v2",
                project_id=project_id,
                error_type=type(e).__name__,
                error_message=str(e),
                error_details=repr(e),
            )
            raise handle_database_error("creating project subscription", e)
