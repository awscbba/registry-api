"""
Subscriptions service implementation.
Handles business logic for subscription operations.
Follows Clean Architecture principles with proper dependency injection.
"""

from typing import List, Optional
from ..repositories.subscriptions_repository import SubscriptionsRepository
from ..models.subscription import (
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    EnrichedSubscriptionResponse,
)
from ..exceptions.base_exceptions import (
    BusinessLogicException,
    ResourceNotFoundException,
    ValidationException,
    ErrorCode,
    ErrorSeverity,
)
from ..services.logging_service import (
    logging_service,
    LogLevel,
    LogCategory,
)


class SubscriptionsService:
    """Service for subscription business logic with enterprise patterns."""

    def __init__(
        self,
        subscriptions_repository: SubscriptionsRepository = None,
        projects_service=None,
        people_service=None,
        email_service=None,
    ):
        """Initialize service with dependency injection.

        Args:
            subscriptions_repository: Repository for subscription data access
            projects_service: Service for project operations (injected to avoid circular imports)
            people_service: Service for people operations (injected to avoid circular imports)
            email_service: Service for email operations (injected to avoid circular imports)
        """
        self.subscriptions_repository = (
            subscriptions_repository or SubscriptionsRepository()
        )
        self._projects_service = projects_service
        self._people_service = people_service
        self._email_service = email_service

    def _get_projects_service(self):
        """Lazy load projects service to avoid circular imports."""
        if self._projects_service is None:
            from ..services.service_registry_manager import service_registry

            self._projects_service = service_registry.get_projects_service()
        return self._projects_service

    def _get_people_service(self):
        """Lazy load people service to avoid circular imports."""
        if self._people_service is None:
            from ..services.service_registry_manager import service_registry

            self._people_service = service_registry.get_people_service()
        return self._people_service

    def _get_email_service(self):
        """Lazy load email service to avoid circular imports."""
        if self._email_service is None:
            from ..services.service_registry_manager import service_registry

            self._email_service = service_registry.get_email_service()
        return self._email_service

    def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription with enterprise validation.

        Args:
            subscription_data: Subscription creation data

        Returns:
            Created subscription response

        Raises:
            BusinessLogicException: If subscription already exists
            ValidationException: If input data is invalid
        """
        # Log subscription creation attempt
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Creating new subscription",
            additional_data={
                "person_id": subscription_data.personId,
                "project_id": subscription_data.projectId,
            },
        )

        # Check if subscription already exists
        existing = self.subscriptions_repository.subscription_exists(
            subscription_data.personId, subscription_data.projectId
        )
        if existing:
            logging_service.log_structured(
                level=LogLevel.WARNING,
                category=LogCategory.SUBSCRIPTION_OPERATIONS,
                message="Attempted to create duplicate subscription",
                additional_data={
                    "person_id": subscription_data.personId,
                    "project_id": subscription_data.projectId,
                },
            )
            raise BusinessLogicException(
                message=f"Subscription already exists for person {subscription_data.personId} and project {subscription_data.projectId}",
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                user_message="You are already subscribed to this project",
                severity=ErrorSeverity.LOW,
            )

        try:
            # Create subscription
            subscription = self.subscriptions_repository.create(subscription_data)

            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SUBSCRIPTION_OPERATIONS,
                message="Subscription created successfully",
                additional_data={
                    "subscription_id": subscription.id,
                    "person_id": subscription.personId,
                    "project_id": subscription.projectId,
                },
            )

            # Convert to response format
            return SubscriptionResponse(**subscription.model_dump())

        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Failed to create subscription: {str(e)}",
                additional_data={
                    "person_id": subscription_data.personId,
                    "project_id": subscription_data.projectId,
                    "error": str(e),
                },
            )
            raise ValidationException(
                message=f"Failed to create subscription: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                user_message="Unable to create subscription at this time",
                cause=e,
            )

    def get_subscription(self, subscription_id: str) -> Optional[SubscriptionResponse]:
        """Get a subscription by ID."""
        subscription = self.subscriptions_repository.get_by_id(subscription_id)
        if not subscription:
            return None

        return SubscriptionResponse(**subscription.model_dump())

    def list_subscriptions(
        self, limit: Optional[int] = None
    ) -> List[SubscriptionResponse]:
        """List all subscriptions."""
        subscriptions = self.subscriptions_repository.list_all(limit=limit)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    async def get_person_subscriptions(
        self, person_id: str
    ) -> List[EnrichedSubscriptionResponse]:
        """Get all subscriptions for a person enriched with project details.

        Args:
            person_id: ID of the person

        Returns:
            List of enriched subscription responses with project details
        """
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Retrieving person subscriptions",
            additional_data={"person_id": person_id},
        )

        subscriptions = self.subscriptions_repository.get_by_person(person_id)

        # Enrich subscriptions with project details
        enriched_subscriptions = []
        for sub in subscriptions:
            enriched_sub = await self._enrich_subscription_with_project(sub)
            enriched_subscriptions.append(enriched_sub)

        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Retrieved person subscriptions",
            additional_data={
                "person_id": person_id,
                "count": len(enriched_subscriptions),
            },
        )

        return enriched_subscriptions

    async def _enrich_subscription_with_project(
        self, subscription: Subscription
    ) -> EnrichedSubscriptionResponse:
        """Enrich a subscription with project details.

        Args:
            subscription: Base subscription object

        Returns:
            Enriched subscription with project details
        """
        # Start with base subscription data
        enriched_data = subscription.model_dump()

        # Get project details
        try:
            projects_service = self._get_projects_service()
            project = await projects_service.get_project(subscription.projectId)

            if project:
                enriched_data.update(
                    {
                        "projectName": project.name,
                        "projectDescription": project.description,
                        "projectStatus": project.status,
                    }
                )
                logging_service.log_structured(
                    level=LogLevel.DEBUG,
                    category=LogCategory.SUBSCRIPTION_OPERATIONS,
                    message="Enriched subscription with project details",
                    additional_data={
                        "subscription_id": subscription.id,
                        "project_id": subscription.projectId,
                    },
                )
            else:
                # Project not found - likely deleted
                enriched_data.update(
                    {
                        "projectName": "[DELETED] Project Not Found",
                        "projectDescription": "This project no longer exists",
                        "projectStatus": "deleted",
                    }
                )
                logging_service.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.SUBSCRIPTION_OPERATIONS,
                    message="Project not found for subscription",
                    additional_data={
                        "subscription_id": subscription.id,
                        "project_id": subscription.projectId,
                    },
                )

        except Exception as e:
            # Error loading project details
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Failed to enrich subscription with project details: {str(e)}",
                additional_data={
                    "subscription_id": subscription.id,
                    "project_id": subscription.projectId,
                    "error": str(e),
                },
            )
            enriched_data.update(
                {
                    "projectName": "[ERROR] Unable to load project",
                    "projectDescription": "Error loading project details",
                    "projectStatus": "unknown",
                }
            )

        return EnrichedSubscriptionResponse(**enriched_data)

    async def get_project_subscriptions(
        self, project_id: str
    ) -> List[EnrichedSubscriptionResponse]:
        """Get all subscriptions for a project enriched with person details.

        Args:
            project_id: ID of the project

        Returns:
            List of enriched subscription responses with person details
        """
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Retrieving project subscriptions",
            additional_data={"project_id": project_id},
        )

        subscriptions = self.subscriptions_repository.get_by_project(project_id)

        # Enrich subscriptions with person details
        enriched_subscriptions = []
        for sub in subscriptions:
            enriched_sub = self._enrich_subscription_with_person(sub)
            enriched_subscriptions.append(enriched_sub)

        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Retrieved project subscriptions",
            additional_data={
                "project_id": project_id,
                "count": len(enriched_subscriptions),
            },
        )

        return enriched_subscriptions

    def _enrich_subscription_with_person(
        self, subscription: Subscription
    ) -> EnrichedSubscriptionResponse:
        """Enrich a subscription with person details.

        Args:
            subscription: Base subscription object

        Returns:
            Enriched subscription with person details
        """
        # Start with base subscription data
        enriched_data = subscription.model_dump()

        # Get person details
        try:
            people_service = self._get_people_service()
            person = people_service.get_person(subscription.personId)

            if person:
                enriched_data.update(
                    {
                        "personName": f"{person.firstName} {person.lastName}".strip(),
                        "personEmail": person.email,
                        "personFirstName": person.firstName,
                        "personLastName": person.lastName,
                    }
                )
                logging_service.log_structured(
                    level=LogLevel.DEBUG,
                    category=LogCategory.SUBSCRIPTION_OPERATIONS,
                    message="Enriched subscription with person details",
                    additional_data={
                        "subscription_id": subscription.id,
                        "person_id": subscription.personId,
                    },
                )
            else:
                # Person not found - likely deleted
                enriched_data.update(
                    {
                        "personName": "Unknown User",
                        "personEmail": "unknown@example.com",
                        "personFirstName": "Unknown",
                        "personLastName": "User",
                    }
                )
                logging_service.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.SUBSCRIPTION_OPERATIONS,
                    message="Person not found for subscription",
                    additional_data={
                        "subscription_id": subscription.id,
                        "person_id": subscription.personId,
                    },
                )

        except Exception as e:
            # Error loading person details
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Failed to enrich subscription with person details: {str(e)}",
                additional_data={
                    "subscription_id": subscription.id,
                    "person_id": subscription.personId,
                    "error": str(e),
                },
            )
            enriched_data.update(
                {
                    "personName": "Unknown User",
                    "personEmail": "unknown@example.com",
                    "personFirstName": "Unknown",
                    "personLastName": "User",
                }
            )

        return EnrichedSubscriptionResponse(**enriched_data)

    def update_subscription(
        self, subscription_id: str, updates: SubscriptionUpdate
    ) -> Optional[SubscriptionResponse]:
        """Update a subscription and send welcome email if approved.

        Args:
            subscription_id: ID of the subscription to update
            updates: Update data

        Returns:
            Updated subscription response or None if not found

        Raises:
            ResourceNotFoundException: If subscription not found
            ValidationException: If update fails
        """
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.SUBSCRIPTION_OPERATIONS,
            message="Updating subscription",
            additional_data={
                "subscription_id": subscription_id,
                "updates": updates.model_dump(exclude_none=True),
            },
        )

        # Get current subscription to check status change
        current_subscription = self.subscriptions_repository.get_by_id(subscription_id)
        if not current_subscription:
            logging_service.log_structured(
                level=LogLevel.WARNING,
                category=LogCategory.SUBSCRIPTION_OPERATIONS,
                message="Subscription not found for update",
                additional_data={"subscription_id": subscription_id},
            )
            raise ResourceNotFoundException(
                message=f"Subscription {subscription_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                user_message="Subscription not found",
            )

        try:
            # Update the subscription
            subscription = self.subscriptions_repository.update(
                subscription_id, updates
            )
            if not subscription:
                raise ValidationException(
                    message=f"Failed to update subscription {subscription_id}",
                    error_code=ErrorCode.DATABASE_ERROR,
                    user_message="Unable to update subscription",
                )

            # Check if status changed from pending to active (approval)
            if current_subscription.status == "pending" and updates.status == "active":
                self._handle_subscription_approval(subscription)

            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SUBSCRIPTION_OPERATIONS,
                message="Subscription updated successfully",
                additional_data={
                    "subscription_id": subscription_id,
                    "status": subscription.status,
                },
            )

            return SubscriptionResponse(**subscription.model_dump())

        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Failed to update subscription: {str(e)}",
                additional_data={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )
            raise

    def _handle_subscription_approval(self, subscription: Subscription) -> None:
        """Handle subscription approval by sending welcome email.

        Args:
            subscription: The approved subscription
        """
        try:
            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.SUBSCRIPTION_OPERATIONS,
                message="Handling subscription approval",
                additional_data={
                    "subscription_id": subscription.id,
                    "person_id": subscription.personId,
                    "project_id": subscription.projectId,
                },
            )

            # Get person and project details
            people_service = self._get_people_service()
            projects_service = self._get_projects_service()
            email_service = self._get_email_service()

            person = people_service.get_person(subscription.personId)
            project = projects_service.get_project(subscription.projectId)

            if person and project:
                # Note: Email service may be async, handle accordingly
                # For now, we'll attempt synchronous call
                # TODO: Implement proper async handling if email_service is async
                try:
                    email_service.send_project_welcome_email(
                        person.email, person.firstName, project.name
                    )
                    logging_service.log_structured(
                        level=LogLevel.INFO,
                        category=LogCategory.EMAIL_OPERATIONS,
                        message="Welcome email sent for subscription approval",
                        additional_data={
                            "subscription_id": subscription.id,
                            "recipient": person.email,
                        },
                    )
                except Exception as email_error:
                    # Log but don't fail the subscription update
                    logging_service.log_structured(
                        level=LogLevel.ERROR,
                        category=LogCategory.EMAIL_OPERATIONS,
                        message=f"Failed to send welcome email: {str(email_error)}",
                        additional_data={
                            "subscription_id": subscription.id,
                            "person_id": subscription.personId,
                            "error": str(email_error),
                        },
                    )
            else:
                logging_service.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.SUBSCRIPTION_OPERATIONS,
                    message="Cannot send welcome email - person or project not found",
                    additional_data={
                        "subscription_id": subscription.id,
                        "person_found": person is not None,
                        "project_found": project is not None,
                    },
                )

        except Exception as e:
            # Log error but don't fail the subscription update
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Error handling subscription approval: {str(e)}",
                additional_data={
                    "subscription_id": subscription.id,
                    "error": str(e),
                },
            )

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        return self.subscriptions_repository.delete(subscription_id)

    def check_subscription_exists(self, person_id: str, project_id: str) -> bool:
        """Check if a subscription exists for a person and project."""
        return self.subscriptions_repository.subscription_exists(person_id, project_id)
