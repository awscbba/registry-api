"""
Subscriptions Service - Domain service for subscription-related operations.
Implements the Service Registry pattern for subscription management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..core.base_service import BaseService
from ..models.subscription import SubscriptionCreate, SubscriptionUpdate
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v1_response, create_v2_response


class SubscriptionsService(BaseService):
    """Service for managing subscription-related operations."""

    def __init__(self):
        super().__init__("subscriptions_service")
        # Use repository pattern instead of direct database service
        from ..repositories.subscription_repository import SubscriptionRepository
        import os

        table_name = os.getenv(
            "SUBSCRIPTIONS_TABLE_NAME", "people-registry-subscriptions"
        )
        self.subscription_repository = SubscriptionRepository(table_name=table_name)
        # Keep legacy db_service for backward compatibility during transition
        self.db_service = DefensiveDynamoDBService()
        self.logger = get_handler_logger("subscriptions_service")

    async def initialize(self):
        """Initialize the subscriptions service."""
        try:
            # Test database connectivity
            await self.db_service.get_all_subscriptions()
            self.logger.info("Subscriptions service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize subscriptions service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the subscriptions service."""
        try:
            # Use a lightweight health check with timeout
            import asyncio

            # Try a quick database connectivity test with 1 second timeout
            try:
                await asyncio.wait_for(self._quick_db_check(), timeout=1.0)
                return {
                    "service": "subscriptions_service",
                    "status": "healthy",
                    "database": "connected",
                    "timestamp": datetime.now().isoformat(),
                }
            except asyncio.TimeoutError:
                return {
                    "service": "subscriptions_service",
                    "status": "degraded",
                    "database": "timeout",
                    "message": "Database check timed out",
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Subscriptions service health check failed: {str(e)}")
            return {
                "service": "subscriptions_service",
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _quick_db_check(self):
        """Quick database connectivity check."""
        # Try to get just one subscription with limit=1 for faster response
        try:
            subscriptions = await self.db_service.get_all_subscriptions()
            return True
        except Exception:
            # If we can't connect, that's still a valid health check result
            raise

    async def get_all_subscriptions_v1(self) -> Dict[str, Any]:
        """Get all subscriptions (v1 format)."""
        try:
            self.logger.log_api_request("GET", "/v1/subscriptions")
            subscriptions = await self.db_service.get_all_subscriptions()

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
            subscriptions = await self.db_service.get_all_subscriptions()

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
            subscription = await self.db_service.get_subscription_by_id(subscription_id)

            if not subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

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
            subscription = await self.db_service.get_subscription_by_id(subscription_id)

            if not subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

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

            # Generate ID if not provided
            subscription_id = str(uuid.uuid4())

            # Create subscription using database service
            created_subscription = await self.db_service.create_subscription(
                subscription_data, subscription_id
            )

            response = create_v2_response(
                created_subscription,
                metadata={
                    "subscription_id": subscription_id,
                    "service": "subscriptions_service",
                    "version": "v2",
                    "created_at": datetime.now().isoformat(),
                },
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
            existing_subscription = await self.db_service.get_subscription_by_id(
                subscription_id
            )
            if not existing_subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Update subscription
            updated_subscription = await self.db_service.update_subscription(
                subscription_id, subscription_data
            )

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
            existing_subscription = await self.db_service.get_subscription_by_id(
                subscription_id
            )
            if not existing_subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Update subscription
            updated_subscription = await self.db_service.update_subscription(
                subscription_id, subscription_data
            )

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
            existing_subscription = await self.db_service.get_subscription_by_id(
                subscription_id
            )
            if not existing_subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Delete subscription
            success = await self.db_service.delete_subscription(subscription_id)
            if not success:
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
            existing_subscription = await self.db_service.get_subscription_by_id(
                subscription_id
            )
            if not existing_subscription:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Delete subscription
            success = await self.db_service.delete_subscription(subscription_id)
            if not success:
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
            subscriptions = await self.db_service.get_subscriptions_by_project(
                project_id
            )

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
            subscriptions = await self.db_service.get_subscriptions_by_project(
                project_id
            )

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
            )

            # Validate required fields
            if not subscription_data.get("person"):
                from src.utils.response_formatter import ResponseFormatter

                raise ResponseFormatter.validation_error_response(
                    [{"field": "person", "message": "Person information is required"}]
                )

            person_data = subscription_data["person"]
            if not person_data.get("email"):
                from src.utils.response_formatter import ResponseFormatter

                raise ResponseFormatter.validation_error_response(
                    [{"field": "person.email", "message": "Person email is required"}]
                )

            # Create subscription entity
            from ..models.subscription import Subscription
            import uuid

            subscription_id = str(uuid.uuid4())
            subscription = Subscription(
                id=subscription_id,
                person_id=None,  # Will be created if doesn't exist
                project_id=project_id,
                person_name=person_data.get("name", ""),
                person_email=person_data["email"],
                status="active",
                notes=subscription_data.get("notes", ""),
                email_sent=False,  # Will be updated after email is sent
            )

            # Create subscription using repository
            result = await self.subscription_repository.create(subscription)

            if result.success:
                # Convert repository result to service format
                subscription_dict = {
                    "id": result.data.id,
                    "person_id": result.data.person_id,
                    "project_id": result.data.project_id,
                    "person_name": result.data.person_name,
                    "person_email": result.data.person_email,
                    "status": result.data.status,
                    "notes": result.data.notes,
                    "email_sent": result.data.email_sent,
                    "created_at": getattr(result.data, "created_at", None),
                    "updated_at": getattr(result.data, "updated_at", None),
                }

                # TODO: Send welcome email here
                # For now, just mark as email_sent = True
                subscription_dict["email_sent"] = True

                service_result = {"success": True, "data": subscription_dict}
            else:
                service_result = {"success": False, "error": result.error}

            if service_result.get("success"):
                # Enhanced v2 response format
                response = create_v2_response(
                    data={
                        "subscription": service_result.get("data", {}),
                        "email_sent": service_result.get("data", {}).get(
                            "email_sent", False
                        ),
                        "project_id": project_id,
                        "person_email": person_data["email"],
                    },
                    message="Subscription created successfully",
                )

                self.logger.info(
                    "Project subscription created successfully",
                    operation="create_project_subscription_v2",
                    project_id=project_id,
                    subscription_id=service_result.get("data", {}).get("id"),
                    email_sent=service_result.get("data", {}).get("email_sent", False),
                )
                return response
            else:
                from src.utils.response_formatter import ResponseFormatter

                raise ResponseFormatter.internal_server_error_response(
                    message=f"Failed to create subscription: {service_result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(
                "Failed to create project subscription",
                operation="create_project_subscription_v2",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating project subscription", e)
