"""
Defensive DynamoDB Service

This is a refactored version of the DynamoDB service that uses defensive programming
patterns to prevent the types of bugs we've been encountering.

Key improvements:
1. Safe type handling for all datetime operations
2. Safe enum value extraction
3. Comprehensive error handling
4. Consistent field mapping
5. Defensive model conversion
"""

import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid
import logging

from ..models.person import Person, PersonCreate, PersonUpdate
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.subscription import SubscriptionCreate, SubscriptionUpdate
from ..models.error_handling import ErrorContext
from ..utils.defensive_utils import (
    safe_isoformat,
    safe_enum_value,
    safe_datetime_parse,
    safe_field_access,
    safe_model_dump,
    database_operation,
    safe_update_expression_builder,
    validate_required_fields,
    sanitize_for_logging,
)


class DefensiveDynamoDBService:
    """
    Defensive version of DynamoDB service with comprehensive error handling
    and type safety.
    """

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.dynamodb_client = boto3.client("dynamodb")
        self.table_name = os.environ.get("PEOPLE_TABLE_NAME", "PeopleTable")
        self.table = self.dynamodb.Table(self.table_name)

        # Additional tables
        self.projects_table_name = os.environ.get(
            "PROJECTS_TABLE_NAME", "ProjectsTable"
        )
        self.subscriptions_table_name = os.environ.get(
            "SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable"
        )

        self.logger = logging.getLogger(__name__)

        try:
            self.projects_table = self.dynamodb.Table(self.projects_table_name)
            self.subscriptions_table = self.dynamodb.Table(
                self.subscriptions_table_name
            )
        except Exception as e:
            self.logger.warning(f"Error initializing additional tables: {e}")
            self.projects_table = None
            self.subscriptions_table = None

    def _safe_person_to_item(self, person: Person) -> Dict[str, Any]:
        """Safely convert Person model to DynamoDB item"""
        try:
            item = {
                "id": person.id,
                "firstName": safe_field_access(person, "first_name", ""),
                "lastName": safe_field_access(person, "last_name", ""),
                "email": safe_field_access(person, "email", ""),
                "phone": safe_field_access(person, "phone", ""),
                "dateOfBirth": safe_field_access(person, "date_of_birth", ""),
                "isAdmin": safe_field_access(person, "is_admin", False),
                "createdAt": safe_isoformat(safe_field_access(person, "created_at")),
                "updatedAt": safe_isoformat(safe_field_access(person, "updated_at")),
            }

            # Handle address safely
            address = safe_field_access(person, "address")
            if address:
                address_dict = safe_model_dump(address)
                item["address"] = self._normalize_address_for_storage(address_dict)
            else:
                item["address"] = {}

            # Handle optional datetime fields safely
            last_password_change = safe_field_access(person, "last_password_change")
            if last_password_change:
                item["lastPasswordChange"] = safe_isoformat(last_password_change)

            account_locked_until = safe_field_access(person, "account_locked_until")
            if account_locked_until:
                item["accountLockedUntil"] = safe_isoformat(account_locked_until)

            last_login_at = safe_field_access(person, "last_login_at")
            if last_login_at:
                item["lastLoginAt"] = safe_isoformat(last_login_at)

            # Handle other optional fields
            item["isActive"] = safe_field_access(person, "is_active", True)
            item["requirePasswordChange"] = safe_field_access(
                person, "require_password_change", False
            )
            item["failedLoginAttempts"] = safe_field_access(
                person, "failed_login_attempts", 0
            )
            item["emailVerified"] = safe_field_access(person, "email_verified", False)

            return item

        except Exception as e:
            self.logger.error(f"Error converting person to item: {e}")
            raise Exception(f"Failed to convert person to database item: {str(e)}")

    def _safe_item_to_person(self, item: Dict[str, Any]) -> Person:
        """Safely convert DynamoDB item to Person model"""
        try:
            # Handle address field safely
            address_data = item.get("address", {})
            if address_data and isinstance(address_data, dict):
                # Normalize postal code field
                if "postal_code" in address_data:
                    address_data["postalCode"] = address_data.pop("postal_code")
                elif "zip_code" in address_data:
                    address_data["postalCode"] = address_data.pop("zip_code")

            # Build person data with safe field access
            person_data = {
                "id": item.get("id", ""),
                "firstName": item.get("firstName", ""),
                "lastName": item.get("lastName", ""),
                "email": item.get("email", ""),
                "phone": item.get("phone", ""),
                "dateOfBirth": item.get("dateOfBirth", ""),
                "address": address_data,
                "isAdmin": item.get("isAdmin", False),
                "createdAt": safe_datetime_parse(item.get("createdAt"))
                or datetime.utcnow(),
                "updatedAt": safe_datetime_parse(item.get("updatedAt"))
                or datetime.utcnow(),
            }

            person = Person(**person_data)

            # Handle optional datetime fields safely
            if item.get("lastPasswordChange"):
                person.last_password_change = safe_datetime_parse(
                    item["lastPasswordChange"]
                )

            if item.get("accountLockedUntil"):
                person.account_locked_until = safe_datetime_parse(
                    item["accountLockedUntil"]
                )

            if item.get("lastLoginAt"):
                person.last_login_at = safe_datetime_parse(item["lastLoginAt"])

            # Handle other optional fields
            person.is_active = item.get("isActive", True)
            person.require_password_change = item.get("requirePasswordChange", False)
            person.failed_login_attempts = item.get("failedLoginAttempts", 0)
            person.email_verified = item.get("emailVerified", False)

            return person

        except Exception as e:
            self.logger.error(f"Error converting item to person: {e}")
            raise Exception(f"Failed to convert database item to person: {str(e)}")

    def _normalize_address_for_storage(
        self, address_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Safely normalize address field names for storage"""
        if not address_dict:
            return {}

        normalized = address_dict.copy()

        # Convert postalCode to postal_code for consistent storage
        if "postalCode" in normalized:
            normalized["postal_code"] = normalized.pop("postalCode")
        elif "zipCode" in normalized:
            normalized["postal_code"] = normalized.pop("zipCode")

        return normalized

    @database_operation("create_person")
    async def create_person(
        self, person_data: PersonCreate, context: Optional[ErrorContext] = None
    ) -> Person:
        """Create a new person with defensive programming"""
        try:
            # Validate required fields
            person_dict = safe_model_dump(person_data)
            required_fields = ["firstName", "lastName", "email"]
            missing_fields = validate_required_fields(person_dict, required_fields)

            if missing_fields:
                raise ValueError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            person = Person.create_new(person_data)
            item = self._safe_person_to_item(person)

            # Log sanitized data
            sanitized_item = sanitize_for_logging(item)
            self.logger.info(f"Creating person with data: {sanitized_item}")

            self.table.put_item(
                Item=item, ConditionExpression="attribute_not_exists(id)"
            )

            return person

        except ClientError as e:
            self.logger.error(f"DynamoDB error creating person: {e}")
            raise Exception(
                f"Failed to create person: {e.response['Error']['Message']}"
            )
        except Exception as e:
            self.logger.error(f"Error creating person: {e}")
            raise

    @database_operation("update_person")
    async def update_person(
        self,
        person_id: str,
        person_update: PersonUpdate,
        context: Optional[ErrorContext] = None,
    ) -> Optional[Person]:
        """Update a person with comprehensive defensive programming"""
        try:
            # Get existing person
            existing_person = await self.get_person(person_id, context)
            if not existing_person:
                return None

            # Get update data safely
            update_data = safe_model_dump(person_update, exclude_unset=True)

            if not update_data:
                self.logger.info(f"No fields to update for person {person_id}")
                return existing_person

            # Build update expression safely
            field_mappings = {
                "first_name": "firstName",
                "last_name": "lastName",
                "date_of_birth": "dateOfBirth",
                "is_admin": "isAdmin",
                "is_active": "isActive",
                "failed_login_attempts": "failedLoginAttempts",
                "account_locked_until": "accountLockedUntil",
                "require_password_change": "requirePasswordChange",
                "last_password_change": "lastPasswordChange",
                "last_login_at": "lastLoginAt",
            }

            update_expression, expression_values, expression_names = (
                safe_update_expression_builder(update_data, field_mappings)
            )

            # Handle address field specially
            if "address" in update_data:
                address_value = update_data["address"]
                if address_value is not None:
                    if isinstance(address_value, dict):
                        address_dict = address_value
                    else:
                        address_dict = safe_model_dump(address_value)

                    normalized_address = self._normalize_address_for_storage(
                        address_dict
                    )
                    expression_values[":address"] = normalized_address
                    update_expression += ", address = :address"
                else:
                    expression_values[":address"] = {}
                    update_expression += ", address = :address"

            # Log sanitized update data
            sanitized_data = sanitize_for_logging(update_data)
            self.logger.info(f"Updating person {person_id} with data: {sanitized_data}")

            # Perform update
            response = self.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues="ALL_NEW",
            )

            updated_person = self._safe_item_to_person(response["Attributes"])
            return updated_person

        except ClientError as e:
            self.logger.error(f"DynamoDB error updating person {person_id}: {e}")
            raise Exception(
                f"Failed to update person: {e.response['Error']['Message']}"
            )
        except Exception as e:
            self.logger.error(f"Error updating person {person_id}: {e}")
            raise

    @database_operation("get_person")
    async def get_person(
        self, person_id: str, context: Optional[ErrorContext] = None
    ) -> Optional[Person]:
        """Get a person by ID with defensive programming"""
        try:
            response = self.table.get_item(Key={"id": person_id})

            if "Item" in response:
                return self._safe_item_to_person(response["Item"])

            return None

        except ClientError as e:
            self.logger.error(f"DynamoDB error getting person {person_id}: {e}")
            raise Exception(f"Failed to get person: {e.response['Error']['Message']}")
        except Exception as e:
            self.logger.error(f"Error getting person {person_id}: {e}")
            raise

    # Project operations with defensive programming
    @database_operation("create_project")
    def create_project(
        self, project_data: ProjectCreate, created_by: str = "system"
    ) -> Dict[str, Any]:
        """Create a project with defensive programming"""
        if not self.projects_table:
            raise Exception("Projects table not available")

        try:
            project_dict = safe_model_dump(project_data)
            required_fields = [
                "name",
                "description",
                "startDate",
                "endDate",
                "maxParticipants",
            ]
            missing_fields = validate_required_fields(project_dict, required_fields)

            if missing_fields:
                raise ValueError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            project_id = str(uuid.uuid4())
            now = datetime.utcnow()

            item = {
                "id": project_id,
                "name": project_data.name,
                "description": project_data.description,
                "startDate": project_data.startDate,
                "endDate": project_data.endDate,
                "maxParticipants": project_data.maxParticipants,
                "status": safe_enum_value(project_data.status, "active"),
                "category": safe_field_access(project_data, "category", ""),
                "location": safe_field_access(project_data, "location", ""),
                "requirements": safe_field_access(project_data, "requirements", ""),
                "createdBy": created_by,
                "createdAt": safe_isoformat(now),
                "updatedAt": safe_isoformat(now),
            }

            self.projects_table.put_item(Item=item)
            return item

        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            raise

    @database_operation("update_project")
    def update_project(
        self, project_id: str, project_data: ProjectUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a project with defensive programming"""
        if not self.projects_table:
            return None

        try:
            update_data = safe_model_dump(project_data, exclude_unset=True)

            if not update_data:
                return None

            field_mappings = {"maxParticipants": "maxParticipants"}

            update_expression, expression_values, expression_names = (
                safe_update_expression_builder(update_data, field_mappings)
            )

            # Handle status field specially
            if "status" in update_data:
                expression_values[":status"] = safe_enum_value(update_data["status"])
                if "status" not in expression_names:
                    expression_names["#status"] = "status"
                    update_expression += ", #status = :status"

            response = self.projects_table.update_item(
                Key={"id": project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues="ALL_NEW",
            )

            return response.get("Attributes")

        except Exception as e:
            self.logger.error(f"Error updating project {project_id}: {e}")
            raise

    # Subscription operations with defensive programming
    @database_operation("create_subscription")
    def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> Dict[str, Any]:
        """Create a subscription with defensive programming"""
        if not self.subscriptions_table:
            raise Exception("Subscriptions table not available")

        try:
            subscription_dict = safe_model_dump(subscription_data)
            required_fields = ["personId", "projectId"]
            missing_fields = validate_required_fields(
                subscription_dict, required_fields
            )

            if missing_fields:
                raise ValueError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            subscription_id = str(uuid.uuid4())
            now = datetime.utcnow()

            item = {
                "id": subscription_id,
                "personId": subscription_data.personId,
                "projectId": subscription_data.projectId,
                "status": safe_enum_value(subscription_data.status, "active"),
                "notes": safe_field_access(subscription_data, "notes", ""),
                "createdAt": safe_isoformat(now),
                "updatedAt": safe_isoformat(now),
            }

            self.subscriptions_table.put_item(Item=item)
            return item

        except Exception as e:
            self.logger.error(f"Error creating subscription: {e}")
            raise

    @database_operation("update_subscription")
    def update_subscription(
        self, subscription_id: str, subscription_data: SubscriptionUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a subscription with defensive programming"""
        if not self.subscriptions_table:
            return None

        try:
            update_data = safe_model_dump(subscription_data, exclude_unset=True)

            if not update_data:
                return None

            update_expression, expression_values, expression_names = (
                safe_update_expression_builder(update_data)
            )

            # Handle status field specially
            if "status" in update_data:
                expression_values[":status"] = safe_enum_value(update_data["status"])
                if "status" not in expression_names:
                    expression_names["#status"] = "status"
                    update_expression += ", #status = :status"

            response = self.subscriptions_table.update_item(
                Key={"id": subscription_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues="ALL_NEW",
            )

            return response.get("Attributes")

        except Exception as e:
            self.logger.error(f"Error updating subscription {subscription_id}: {e}")
            raise
