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
from ..models.auth import SecurityEvent, AccountLockout
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.subscription import SubscriptionCreate, SubscriptionUpdate
from ..models.error_handling import ErrorContext


class DynamoDBService:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.dynamodb_client = boto3.client("dynamodb")
        self.table_name = os.environ.get("PEOPLE_TABLE_NAME", "PeopleTable")
        self.table = self.dynamodb.Table(self.table_name)

        # Additional tables for authentication
        self.audit_table_name = os.environ.get("AUDIT_TABLE_NAME", "AuditLogsTable")
        self.lockout_table_name = os.environ.get(
            "LOCKOUT_TABLE_NAME", "AccountLockoutTable"
        )

        # New tables for projects and subscriptions
        self.projects_table_name = os.environ.get(
            "PROJECTS_TABLE_NAME", "ProjectsTable"
        )
        self.subscriptions_table_name = os.environ.get(
            "SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable"
        )

        # Setup logging
        self.logger = logging.getLogger(__name__)

        try:
            self.audit_table = self.dynamodb.Table(self.audit_table_name)
            self.lockout_table = self.dynamodb.Table(self.lockout_table_name)
            self.projects_table = self.dynamodb.Table(self.projects_table_name)
            self.subscriptions_table = self.dynamodb.Table(
                self.subscriptions_table_name
            )

            # Check if email GSI exists, if not, try to create it
            self._check_email_gsi()
        except Exception as e:
            # Tables might not exist yet, will be created by infrastructure
            self.logger.warning(f"Error initializing DynamoDB tables: {e}")
            self.audit_table = None
            self.lockout_table = None
            self.projects_table = None
            self.subscriptions_table = None

    def _check_email_gsi(self):
        """Check if email GSI exists and create it if possible"""
        try:
            # Get table description to check for GSIs
            table_description = self.dynamodb_client.describe_table(
                TableName=self.table_name
            )

            # Check if EmailIndex GSI exists
            gsi_exists = False
            if "GlobalSecondaryIndexes" in table_description["Table"]:
                for gsi in table_description["Table"]["GlobalSecondaryIndexes"]:
                    if gsi["IndexName"] == "EmailIndex":
                        gsi_exists = True
                        self.logger.info("EmailIndex GSI found on people table")
                        break

            if not gsi_exists:
                self.logger.warning(
                    "EmailIndex GSI not found on people table. Email uniqueness checks will use scan operations."
                )
                # Note: Creating a GSI requires UpdateTable permissions and can be expensive
                # In a production environment, GSIs should be created through infrastructure as code
                # This is just a placeholder for where you would create the GSI if needed
        except Exception as e:
            self.logger.warning(f"Error checking for email GSI: {e}")
            # Continue without GSI - will fall back to scan operations

    async def _log_database_operation(
        self,
        operation: str,
        table_name: str,
        record_id: str,
        context: Optional[ErrorContext] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        """Log database operations for comprehensive audit trail"""
        try:
            audit_entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "operation": operation,
                "table_name": table_name,
                "record_id": record_id,
                "success": success,
            }

            if context:
                audit_entry.update(
                    {
                        "user_id": context.user_id if context.user_id else None,
                        "request_id": context.request_id,
                        "ip_address": (
                            context.ip_address if context.ip_address else None
                        ),
                        "user_agent": (
                            context.user_agent if context.user_agent else None
                        ),
                        "path": context.path if context.path else None,
                        "method": context.method if context.method else None,
                    }
                )

                # Include any additional context data
                if hasattr(context, "additional_data") and context.additional_data:
                    if "context_data" not in audit_entry:
                        audit_entry["context_data"] = {}
                    audit_entry["context_data"].update(context.additional_data)

            if before_state:
                # Remove sensitive fields from audit log
                safe_before_state = self._sanitize_audit_data(before_state)
                audit_entry["before_state"] = safe_before_state

            if after_state:
                # Remove sensitive fields from audit log
                safe_after_state = self._sanitize_audit_data(after_state)
                audit_entry["after_state"] = safe_after_state

            if error_message:
                audit_entry["error_message"] = error_message

            if additional_data:
                # Add any additional data provided
                audit_entry["additional_data"] = additional_data

            # Add fields that were changed if both before and after states are available
            if before_state and after_state:
                changed_fields = []
                for key in after_state:
                    if key in before_state and before_state[key] != after_state[key]:
                        changed_fields.append(key)
                if changed_fields:
                    audit_entry["changed_fields"] = changed_fields

            # Log to audit table if available
            if self.audit_table:
                self.audit_table.put_item(Item=audit_entry)

            # Also log to application logger
            log_level = logging.INFO if success else logging.ERROR
            log_message = f"DB Operation: {operation} on {table_name}:{record_id} - {'SUCCESS' if success else 'FAILED'}"

            if error_message:
                log_message += f" - Error: {error_message}"

            if before_state and after_state and "changed_fields" in audit_entry:
                log_message += (
                    f" - Changed fields: {', '.join(audit_entry['changed_fields'])}"
                )

            self.logger.log(log_level, log_message)

            return audit_entry["id"]  # Return the audit entry ID for reference

        except Exception as e:
            # Don't fail the main operation if audit logging fails
            self.logger.error(f"Failed to log database operation: {str(e)}")
            return None

    def _sanitize_audit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive fields from audit log data"""
        if not isinstance(data, dict):
            return data

        sensitive_fields = {
            "passwordHash",
            "password_hash",
            "passwordSalt",
            "password_salt",
            "passwordHistory",
            "password_history",
            "emailVerificationToken",
            "email_verification_token",
        }

        sanitized = {}
        for key, value in data.items():
            if key in sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_audit_data(value)
            else:
                sanitized[key] = value

        return sanitized

    def _handle_database_error(
        self, operation: str, error: ClientError, context: Optional[ErrorContext] = None
    ) -> Exception:
        """Enhanced error handling for database constraint violations with detailed error mapping"""
        error_code = error.response["Error"]["Code"]
        error_message = error.response["Error"]["Message"]

        # Log the error
        self.logger.error(
            f"Database error in {operation}: {error_code} - {error_message}"
        )

        # Map DynamoDB errors to application-specific exceptions with more detailed information
        if error_code == "ConditionalCheckFailedException":
            if "email" in error_message.lower():
                from ..models.error_handling import APIException, ErrorCode

                return APIException(
                    error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    message="Email address already exists in the system",
                    context=context,
                )
            elif "id" in error_message.lower():
                from ..models.error_handling import APIException, ErrorCode

                return APIException(
                    error_code=ErrorCode.DUPLICATE_VALUE,
                    message="Record with this ID already exists",
                    context=context,
                )
            else:
                from ..models.error_handling import APIException, ErrorCode

                return APIException(
                    error_code=ErrorCode.CONSTRAINT_VIOLATION,
                    message="Constraint violation: Record already exists or condition not met",
                    context=context,
                )

        elif error_code == "ValidationException":
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.INVALID_FORMAT,
                message=f"Invalid data format: {error_message}",
                context=context,
            )

        elif error_code == "ResourceNotFoundException":
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Requested resource not found",
                context=context,
            )

        elif error_code == "ProvisionedThroughputExceededException":
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Database capacity exceeded. Please try again later.",
                context=context,
                retry_after=30,  # Suggest retry after 30 seconds
            )

        elif error_code == "ItemCollectionSizeLimitExceededException":
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="Data size limit exceeded for this operation",
                context=context,
            )

        elif error_code == "TransactionConflictException":
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="Transaction conflict. Please retry the operation.",
                context=context,
                retry_after=5,  # Suggest retry after 5 seconds
            )

        else:
            # Generic database error
            from ..models.error_handling import APIException, ErrorCode

            return APIException(
                error_code=ErrorCode.DATABASE_ERROR,
                message=f"Database operation failed: {error_message}",
                context=context,
            )

    async def check_email_uniqueness(
        self,
        email: str,
        exclude_person_id: Optional[str] = None,
        context: Optional[ErrorContext] = None,
    ) -> bool:
        """
        Check if email is unique with proper indexing support.
        This method is optimized for email uniqueness checking using GSI if available.
        """
        try:
            # First, try to use a GSI if available for better performance
            # In a production environment, you would have a GSI on email field
            try:
                # Check if we have a GSI on email
                response = self.table.query(
                    IndexName="EmailIndex",  # This would be the name of your GSI on email
                    KeyConditionExpression=Key("email").eq(email),
                    Limit=1,
                )

                items = response.get("Items", [])

                # Log the GSI usage for monitoring
                await self._log_database_operation(
                    operation="CHECK_EMAIL_UNIQUENESS_GSI",
                    table_name=self.table_name,
                    record_id=f"email:{email}",
                    context=context,
                    success=True,
                    additional_data={"using_gsi": True, "found": len(items) > 0},
                )

                if not items:
                    return True  # Email is unique

                existing_person = self._item_to_person(items[0])

                # If excluding a specific person ID, check if it's the same person
                if exclude_person_id and existing_person.id == exclude_person_id:
                    return True  # Same person, so email is still "unique" for them

                return False  # Email already exists for a different person

            except ClientError as gsi_error:
                # GSI might not exist, fall back to scan
                if (
                    gsi_error.response["Error"]["Code"] == "ValidationException"
                    and "IndexName" in gsi_error.response["Error"]["Message"]
                ):
                    self.logger.warning(
                        "EmailIndex GSI not found, falling back to scan for email uniqueness check"
                    )

                    # Fall back to scan method
                    existing_person = await self.get_person_by_email(email, context)

                    # Log the fallback to scan
                    await self._log_database_operation(
                        operation="CHECK_EMAIL_UNIQUENESS_SCAN",
                        table_name=self.table_name,
                        record_id=f"email:{email}",
                        context=context,
                        success=True,
                        additional_data={
                            "using_gsi": False,
                            "fallback_reason": "GSI not available",
                        },
                    )

                    if existing_person is None:
                        return True  # Email is unique

                    # If excluding a specific person ID, check if it's the same person
                    if exclude_person_id and existing_person.id == exclude_person_id:
                        return True  # Same person, so email is still "unique" for them

                    return False  # Email already exists for a different person
                else:
                    # Some other GSI error, re-raise
                    raise gsi_error

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="CHECK_EMAIL_UNIQUENESS",
                table_name=self.table_name,
                record_id=f"email:{email}",
                context=context,
                success=False,
                error_message=str(e),
            )

            self.logger.error(f"Error checking email uniqueness: {e}")
            # If we can't check uniqueness, assume it's not unique for safety
            return False

    def _person_to_item(self, person: Person) -> Dict[str, Any]:
        """Convert Person model to DynamoDB item with comprehensive password field handling"""
        item = {
            "id": person.id,
            "firstName": person.first_name,
            "lastName": person.last_name,
            "email": person.email,
            "phone": person.phone,
            "dateOfBirth": person.date_of_birth,
            "address": self._normalize_address_for_storage(person.address.model_dump()),
            "createdAt": person.created_at.isoformat(),
            "updatedAt": person.updated_at.isoformat(),
        }

        # Add password-related fields with proper handling
        if hasattr(person, "password_hash") and person.password_hash:
            item["passwordHash"] = person.password_hash
        if hasattr(person, "password_salt") and person.password_salt:
            item["passwordSalt"] = person.password_salt
        if hasattr(person, "require_password_change"):
            item["requirePasswordChange"] = person.require_password_change
        if hasattr(person, "last_password_change") and person.last_password_change:
            item["lastPasswordChange"] = person.last_password_change.isoformat()
        if hasattr(person, "password_history") and person.password_history:
            item["passwordHistory"] = person.password_history
        if hasattr(person, "failed_login_attempts"):
            item["failedLoginAttempts"] = person.failed_login_attempts
        if hasattr(person, "account_locked_until") and person.account_locked_until:
            item["accountLockedUntil"] = person.account_locked_until.isoformat()
        if hasattr(person, "last_login_at") and person.last_login_at:
            item["lastLoginAt"] = person.last_login_at.isoformat()
        if hasattr(person, "is_active"):
            item["isActive"] = person.is_active

        # Add email verification fields
        if hasattr(person, "email_verified"):
            item["emailVerified"] = person.email_verified
        if (
            hasattr(person, "email_verification_token")
            and person.email_verification_token
        ):
            item["emailVerificationToken"] = person.email_verification_token
        if hasattr(person, "pending_email_change") and person.pending_email_change:
            item["pendingEmailChange"] = person.pending_email_change

        return item

    def _normalize_address_for_storage(
        self, address_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize address field names for consistent storage"""
        # Convert postalCode to postal_code for consistent storage
        if "postalCode" in address_dict:
            address_dict["postal_code"] = address_dict.pop("postalCode")
        # Handle legacy zipCode field
        elif "zipCode" in address_dict:
            address_dict["postal_code"] = address_dict.pop("zipCode")
        # Handle legacy zip_code field
        elif "zip_code" in address_dict:
            address_dict["postal_code"] = address_dict.pop("zip_code")
        return address_dict

    def _item_to_person(self, item: Dict[str, Any]) -> Person:
        """Convert DynamoDB item to Person model with comprehensive field handling"""
        # Convert address field to match model expectations
        address_data = item["address"].copy()
        # Handle all possible postal code field variations
        if "postal_code" in address_data:
            address_data["postalCode"] = address_data.pop("postal_code")
        elif "zip_code" in address_data:
            # Handle legacy data that uses zip_code
            address_data["postalCode"] = address_data.pop("zip_code")
        elif "zipCode" in address_data:
            # Handle legacy data that uses zipCode
            address_data["postalCode"] = address_data.pop("zipCode")

        person_data = {
            "id": item["id"],
            "firstName": item["firstName"],
            "lastName": item["lastName"],
            "email": item["email"],
            "phone": item["phone"],
            "dateOfBirth": item["dateOfBirth"],
            "address": address_data,
            "isAdmin": item.get("isAdmin", False),  # Default to False if not present
            "createdAt": datetime.fromisoformat(item["createdAt"]),
            "updatedAt": datetime.fromisoformat(item["updatedAt"]),
        }

        person = Person(**person_data)

        # Add password-related fields if they exist
        if "passwordHash" in item:
            person.password_hash = item["passwordHash"]
        elif "password_hash" in item:  # Support snake_case for backward compatibility
            person.password_hash = item["password_hash"]
        if "passwordSalt" in item:
            person.password_salt = item["passwordSalt"]
        if "requirePasswordChange" in item:
            person.require_password_change = item["requirePasswordChange"]
        if "lastPasswordChange" in item:
            person.last_password_change = datetime.fromisoformat(
                item["lastPasswordChange"]
            )
        if "passwordHistory" in item:
            person.password_history = item["passwordHistory"]
        if "failedLoginAttempts" in item:
            person.failed_login_attempts = item["failedLoginAttempts"]
        if "accountLockedUntil" in item:
            person.account_locked_until = datetime.fromisoformat(
                item["accountLockedUntil"]
            )
        if "lastLoginAt" in item:
            person.last_login_at = datetime.fromisoformat(item["lastLoginAt"])
        if "isActive" in item:
            person.is_active = item["isActive"]
        else:
            person.is_active = True  # Default to active

        # Add email verification fields
        if "emailVerified" in item:
            person.email_verified = item["emailVerified"]
        if "emailVerificationToken" in item:
            person.email_verification_token = item["emailVerificationToken"]
        if "pendingEmailChange" in item:
            person.pending_email_change = item["pendingEmailChange"]

        return person

    async def create_person(
        self, person_data: PersonCreate, context: Optional[ErrorContext] = None
    ) -> Person:
        """Create a new person in DynamoDB with enhanced password field handling and audit logging"""
        person = Person.create_new(person_data)
        item = self._person_to_item(person)

        # Check email uniqueness before creating
        if not await self.check_email_uniqueness(person.email):
            await self._log_database_operation(
                operation="CREATE_PERSON",
                table_name=self.table_name,
                record_id=person.id,
                context=context,
                success=False,
                error_message="Email address already exists",
            )
            raise ValueError("Email address already exists in the system")

        try:
            # Use condition expression to ensure both ID and email uniqueness
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(id) AND attribute_not_exists(email)",
            )

            # Log successful creation
            await self._log_database_operation(
                operation="CREATE_PERSON",
                table_name=self.table_name,
                record_id=person.id,
                context=context,
                after_state=item,
                success=True,
            )

            return person

        except ClientError as e:
            # Enhanced error handling with audit logging
            await self._log_database_operation(
                operation="CREATE_PERSON",
                table_name=self.table_name,
                record_id=person.id,
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("create_person", e, context)

    async def get_person(
        self, person_id: str, context: Optional[ErrorContext] = None
    ) -> Optional[Person]:
        """Get a person by ID with audit logging"""
        try:
            response = self.table.get_item(Key={"id": person_id})

            if "Item" in response:
                person = self._item_to_person(response["Item"])

                # Log successful access
                await self._log_database_operation(
                    operation="GET_PERSON",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    success=True,
                )

                return person
            else:
                # Log access attempt for non-existent person
                await self._log_database_operation(
                    operation="GET_PERSON",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    success=False,
                    error_message="Person not found",
                )

            return None

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="GET_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("get_person", e, context)

    async def list_people(
        self, limit: int = 100, context: Optional[ErrorContext] = None
    ) -> List[Person]:
        """List all people with optional limit and audit logging"""
        try:
            response = self.table.scan(Limit=limit)
            people = []
            for item in response.get("Items", []):
                people.append(self._item_to_person(item))

            # Log successful list operation
            await self._log_database_operation(
                operation="LIST_PEOPLE",
                table_name=self.table_name,
                record_id="all",
                context=context,
                success=True,
                additional_data={"count": len(people), "limit": limit},
            )

            return people

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="LIST_PEOPLE",
                table_name=self.table_name,
                record_id="all",
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("list_people", e, context)

    async def update_person(
        self,
        person_id: str,
        person_update: PersonUpdate,
        context: Optional[ErrorContext] = None,
    ) -> Optional[Person]:
        """Update a person by ID with enhanced password field handling and audit logging"""
        # First, get the existing person
        existing_person = await self.get_person(person_id, context)
        if not existing_person:
            await self._log_database_operation(
                operation="UPDATE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message="Person not found",
            )
            return None

        # Store before state for audit logging
        before_state = self._person_to_item(existing_person)

        # Check email uniqueness if email is being updated
        update_data = person_update.model_dump(exclude_unset=True)
        if "email" in update_data:
            if not await self.check_email_uniqueness(update_data["email"], person_id):
                await self._log_database_operation(
                    operation="UPDATE_PERSON",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    before_state=before_state,
                    success=False,
                    error_message="Email address already exists",
                )
                raise ValueError("Email address already exists in the system")

        # Prepare update expression
        update_expression = "SET updatedAt = :updated_at"
        expression_attribute_values = {":updated_at": datetime.utcnow().isoformat()}

        # Build update expression dynamically with comprehensive field support
        for field, value in update_data.items():
            if field == "first_name":
                update_expression += ", firstName = :first_name"
                expression_attribute_values[":first_name"] = value
            elif field == "last_name":
                update_expression += ", lastName = :last_name"
                expression_attribute_values[":last_name"] = value
            elif field == "email":
                update_expression += ", email = :email"
                expression_attribute_values[":email"] = value
            elif field == "phone":
                update_expression += ", phone = :phone"
                expression_attribute_values[":phone"] = value
            elif field == "date_of_birth":
                update_expression += ", dateOfBirth = :date_of_birth"
                expression_attribute_values[":date_of_birth"] = value
            elif field == "address":
                update_expression += ", address = :address"
                # Ensure address uses the correct field names for storage
                address_dict = value.model_dump()
                # Normalize address field names for storage
                address_dict = self._normalize_address_for_storage(address_dict)
                expression_attribute_values[":address"] = address_dict
            elif field == "is_admin":
                update_expression += ", isAdmin = :is_admin"
                expression_attribute_values[":is_admin"] = value
            elif field == "is_active":
                update_expression += ", isActive = :is_active"
                expression_attribute_values[":is_active"] = value
            elif field == "failed_login_attempts":
                update_expression += ", failedLoginAttempts = :failed_login_attempts"
                expression_attribute_values[":failed_login_attempts"] = value
            elif field == "account_locked_until":
                update_expression += ", accountLockedUntil = :account_locked_until"
                expression_attribute_values[":account_locked_until"] = (
                    value.isoformat() if value else None
                )
            elif field == "require_password_change":
                update_expression += (
                    ", requirePasswordChange = :require_password_change"
                )
                expression_attribute_values[":require_password_change"] = value

        try:
            response = self.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW",
            )

            updated_person = self._item_to_person(response["Attributes"])
            after_state = self._person_to_item(updated_person)

            # Log successful update
            await self._log_database_operation(
                operation="UPDATE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                after_state=after_state,
                success=True,
            )

            return updated_person

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="UPDATE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("update_person", e, context)

    async def update_person_password_fields(
        self,
        person_id: str,
        password_hash: Optional[str] = None,
        password_salt: Optional[str] = None,
        password_history: Optional[List[str]] = None,
        last_password_change: Optional[datetime] = None,
        require_password_change: Optional[bool] = None,
        failed_login_attempts: Optional[int] = None,
        account_locked_until: Optional[datetime] = None,
        context: Optional[ErrorContext] = None,
    ) -> Optional[Person]:
        """Update password-related fields for a person with comprehensive audit logging"""
        # First, get the existing person
        existing_person = await self.get_person(person_id, context)
        if not existing_person:
            await self._log_database_operation(
                operation="UPDATE_PASSWORD_FIELDS",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message="Person not found",
            )
            return None

        # Store before state for audit logging (sanitized)
        before_state = self._person_to_item(existing_person)

        # Prepare update expression for password-related fields
        update_expression = "SET updatedAt = :updated_at"
        expression_attribute_values = {":updated_at": datetime.utcnow().isoformat()}

        # Build update expression for password fields
        if password_hash is not None:
            update_expression += ", passwordHash = :password_hash"
            expression_attribute_values[":password_hash"] = password_hash

        if password_salt is not None:
            update_expression += ", passwordSalt = :password_salt"
            expression_attribute_values[":password_salt"] = password_salt

        if password_history is not None:
            update_expression += ", passwordHistory = :password_history"
            expression_attribute_values[":password_history"] = password_history

        if last_password_change is not None:
            update_expression += ", lastPasswordChange = :last_password_change"
            expression_attribute_values[":last_password_change"] = (
                last_password_change.isoformat()
            )

        if require_password_change is not None:
            update_expression += ", requirePasswordChange = :require_password_change"
            expression_attribute_values[":require_password_change"] = (
                require_password_change
            )

        if failed_login_attempts is not None:
            update_expression += ", failedLoginAttempts = :failed_login_attempts"
            expression_attribute_values[":failed_login_attempts"] = (
                failed_login_attempts
            )

        if account_locked_until is not None:
            update_expression += ", accountLockedUntil = :account_locked_until"
            expression_attribute_values[":account_locked_until"] = (
                account_locked_until.isoformat()
            )

        try:
            response = self.table.update_item(
                Key={"id": person_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW",
            )

            updated_person = self._item_to_person(response["Attributes"])
            after_state = self._person_to_item(updated_person)

            # Log successful password field update
            await self._log_database_operation(
                operation="UPDATE_PASSWORD_FIELDS",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                after_state=after_state,
                success=True,
            )

            return updated_person

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="UPDATE_PASSWORD_FIELDS",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error(
                "update_person_password_fields", e, context
            )

    async def delete_person(
        self, person_id: str, context: Optional[ErrorContext] = None
    ) -> bool:
        """Delete a person by ID with comprehensive audit logging and referential integrity checks"""
        # First, get the existing person for audit logging
        existing_person = await self.get_person(person_id, context)
        if not existing_person:
            await self._log_database_operation(
                operation="DELETE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message="Person not found",
            )
            return False

        # Store before state for audit logging
        before_state = self._person_to_item(existing_person)

        # Check for referential integrity - subscriptions
        try:
            subscriptions = self.get_subscriptions_by_person(person_id)
            if subscriptions:
                await self._log_database_operation(
                    operation="DELETE_PERSON",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    before_state=before_state,
                    success=False,
                    error_message=f"Cannot delete person with {len(subscriptions)} active subscriptions",
                )
                raise ValueError(
                    f"Cannot delete person with {len(subscriptions)} active subscriptions. Please remove subscriptions first."
                )
        except Exception as e:
            if "Cannot delete person with" in str(e):
                raise e
            # If subscription check fails, log but continue (table might not exist)
            self.logger.warning(
                f"Could not check subscriptions for person {person_id}: {e}"
            )

        try:
            response = self.table.delete_item(
                Key={"id": person_id}, ReturnValues="ALL_OLD"
            )

            success = "Attributes" in response

            # Log deletion result
            await self._log_database_operation(
                operation="DELETE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                success=success,
                error_message=(
                    None if success else "Person not found or already deleted"
                ),
            )

            return success

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="DELETE_PERSON",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                before_state=before_state,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("delete_person", e, context)

    async def search_people(
        self,
        search_params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
        context: Optional[ErrorContext] = None,
    ) -> tuple[List[Person], int]:
        """Search for people based on various criteria with pagination and audit logging"""
        try:
            # Build filter expression
            filter_expressions = []
            expression_values = {}

            # Search by email (exact match)
            if search_params.get("email"):
                filter_expressions.append(Attr("email").eq(search_params["email"]))

            # Search by first name (case-insensitive contains)
            if search_params.get("first_name"):
                filter_expressions.append(
                    Attr("firstName").contains(search_params["first_name"])
                )

            # Search by last name (case-insensitive contains)
            if search_params.get("last_name"):
                filter_expressions.append(
                    Attr("lastName").contains(search_params["last_name"])
                )

            # Search by phone (contains - allows partial matches)
            if search_params.get("phone"):
                filter_expressions.append(
                    Attr("phone").contains(search_params["phone"])
                )

            # Filter by active status
            if search_params.get("is_active") is not None:
                filter_expressions.append(
                    Attr("isActive").eq(search_params["is_active"])
                )

            # Filter by email verification status
            if search_params.get("email_verified") is not None:
                filter_expressions.append(
                    Attr("emailVerified").eq(search_params["email_verified"])
                )

            # Combine all filter expressions with AND
            filter_expression = None
            if filter_expressions:
                filter_expression = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    filter_expression = filter_expression & expr

            # First, get total count for pagination metadata
            total_count = 0
            if filter_expression:
                count_response = self.table.scan(
                    FilterExpression=filter_expression, Select="COUNT"
                )
                total_count = count_response.get("Count", 0)
            else:
                # If no filters, get total count of all items
                count_response = self.table.scan(Select="COUNT")
                total_count = count_response.get("Count", 0)

            # Now get the actual data with pagination
            scan_kwargs = {"Limit": limit}

            if filter_expression:
                scan_kwargs["FilterExpression"] = filter_expression

            # Handle pagination with offset
            # Note: DynamoDB doesn't support offset directly, so we need to scan through items
            # This is not the most efficient approach for large datasets, but works for moderate sizes
            items_to_skip = offset
            all_items = []

            while len(all_items) < limit and items_to_skip >= 0:
                response = self.table.scan(**scan_kwargs)
                items = response.get("Items", [])

                if not items:
                    break

                # If we need to skip items, skip them
                if items_to_skip > 0:
                    if items_to_skip >= len(items):
                        items_to_skip -= len(items)
                        # Continue to next batch
                        if "LastEvaluatedKey" in response:
                            scan_kwargs["ExclusiveStartKey"] = response[
                                "LastEvaluatedKey"
                            ]
                        else:
                            break
                        continue
                    else:
                        # Skip partial items and take the rest
                        items = items[items_to_skip:]
                        items_to_skip = 0

                # Add items to result
                remaining_needed = limit - len(all_items)
                all_items.extend(items[:remaining_needed])

                # Check if we have more items to scan
                if "LastEvaluatedKey" in response and len(all_items) < limit:
                    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                else:
                    break

            # Convert items to Person objects
            people = []
            for item in all_items:
                people.append(self._item_to_person(item))

            # Log successful search operation
            await self._log_database_operation(
                operation="SEARCH_PEOPLE",
                table_name=self.table_name,
                record_id="search",
                context=context,
                success=True,
                additional_data={
                    "search_params": search_params,
                    "limit": limit,
                    "offset": offset,
                    "results_count": len(people),
                    "total_count": total_count,
                },
            )

            return people, total_count

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="SEARCH_PEOPLE",
                table_name=self.table_name,
                record_id="search",
                context=context,
                success=False,
                error_message=str(e),
                additional_data={"search_params": search_params},
            )

            raise self._handle_database_error("search_people", e, context)

    # Authentication-related methods

    async def get_person_by_email(
        self, email: str, context: Optional[ErrorContext] = None
    ) -> Optional[Person]:
        """Get a person by email address with optimized indexing and audit logging"""
        try:
            # Use EmailIndex GSI for efficient email lookups
            response = self.table.query(
                IndexName="EmailIndex",
                KeyConditionExpression=Key("email").eq(email),
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                person = self._item_to_person(items[0])

                # Log successful email lookup
                await self._log_database_operation(
                    operation="GET_PERSON_BY_EMAIL",
                    table_name=self.table_name,
                    record_id=person.id,
                    context=context,
                    success=True,
                )

                return person
            else:
                # Log failed email lookup
                await self._log_database_operation(
                    operation="GET_PERSON_BY_EMAIL",
                    table_name=self.table_name,
                    record_id=f"email:{email}",
                    context=context,
                    success=False,
                    error_message="Person not found by email",
                )

            return None

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="GET_PERSON_BY_EMAIL",
                table_name=self.table_name,
                record_id=f"email:{email}",
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("get_person_by_email", e, context)

    async def update_last_login(
        self,
        person_id: str,
        login_time: datetime,
        context: Optional[ErrorContext] = None,
    ):
        """Update the last login timestamp for a person with audit logging"""
        try:
            # First, get the existing person for audit logging
            existing_person = await self.get_person(person_id, context)
            if not existing_person:
                await self._log_database_operation(
                    operation="UPDATE_LAST_LOGIN",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    success=False,
                    error_message="Person not found",
                )
                return False

            # Store before state for audit logging
            before_state = self._person_to_item(existing_person)

            response = self.table.update_item(
                Key={"id": person_id},
                UpdateExpression="SET lastLoginAt = :login_time, updatedAt = :updated_at",
                ExpressionAttributeValues={
                    ":login_time": login_time.isoformat(),
                    ":updated_at": datetime.utcnow().isoformat(),
                },
                ReturnValues="ALL_NEW",
            )

            if "Attributes" in response:
                updated_person = self._item_to_person(response["Attributes"])
                after_state = self._person_to_item(updated_person)

                # Log successful update
                await self._log_database_operation(
                    operation="UPDATE_LAST_LOGIN",
                    table_name=self.table_name,
                    record_id=person_id,
                    context=context,
                    before_state=before_state,
                    after_state=after_state,
                    success=True,
                )

                return True

            return False

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="UPDATE_LAST_LOGIN",
                table_name=self.table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("update_last_login", e, context)

    async def log_security_event(
        self, security_event, context: Optional[ErrorContext] = None
    ):
        """Log a security event to the audit table with enhanced error handling"""
        if not self.audit_table:
            self.logger.warning("Audit table not available, security event not logged")
            return  # Skip if audit table not available

        try:
            # Handle both old SecurityEvent format and new SecurityEvent format
            if hasattr(security_event, "to_dict"):
                # New SecurityEvent model with to_dict method
                item = security_event.to_dict()
            else:
                # Old SecurityEvent format - maintain backward compatibility
                event_id = str(uuid.uuid4())
                item = {
                    "id": event_id,
                    "personId": getattr(security_event, "person_id", None),
                    "action": getattr(security_event, "action", "unknown"),
                    "timestamp": getattr(
                        security_event, "timestamp", datetime.utcnow()
                    ).isoformat(),
                    "success": getattr(security_event, "success", False),
                    "eventType": (
                        getattr(security_event, "event_type", "UNKNOWN").value
                        if hasattr(getattr(security_event, "event_type", None), "value")
                        else getattr(security_event, "event_type", "UNKNOWN")
                    ),
                }

                if hasattr(security_event, "ip_address") and security_event.ip_address:
                    item["ipAddress"] = security_event.ip_address
                if hasattr(security_event, "user_agent") and security_event.user_agent:
                    item["userAgent"] = security_event.user_agent
                if hasattr(security_event, "details") and security_event.details:
                    item["details"] = security_event.details
                if hasattr(security_event, "severity") and security_event.severity:
                    item["severity"] = (
                        security_event.severity.value
                        if hasattr(security_event.severity, "value")
                        else security_event.severity
                    )

            # Add context information if available
            if context:
                if "ipAddress" not in item and context.ip_address:
                    item["ipAddress"] = context.ip_address
                if "userAgent" not in item and context.user_agent:
                    item["userAgent"] = context.user_agent
                if "userId" not in item and context.user_id:
                    item["userId"] = context.user_id
                if "requestId" not in item and context.request_id:
                    item["requestId"] = context.request_id

            # Ensure timestamp exists
            if "timestamp" not in item:
                item["timestamp"] = datetime.utcnow().isoformat()

            # Ensure ID exists
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

            self.audit_table.put_item(Item=item)

            # Log to application logger as well
            self.logger.info(
                f"Security event logged: {item.get('action', 'UNKNOWN')} - ID: {item.get('id')}"
            )

            return item.get("id")  # Return the event ID for reference

        except ClientError as e:
            # Don't fail the main operation if audit logging fails
            self.logger.error(f"Failed to log security event (DynamoDB error): {e}")
            return None
        except Exception as e:
            # Handle any other errors
            self.logger.error(f"Failed to log security event (unexpected error): {e}")
            return None

    async def get_account_lockout(
        self, person_id: str, context: Optional[ErrorContext] = None
    ) -> Optional[AccountLockout]:
        """Get account lockout information for a person with audit logging"""
        if not self.lockout_table:
            self.logger.warning(
                "Lockout table not available, cannot get account lockout information"
            )
            return None

        try:
            response = self.lockout_table.get_item(Key={"personId": person_id})

            if "Item" in response:
                item = response["Item"]
                lockout = AccountLockout(
                    person_id=item["personId"],
                    failed_attempts=item.get("failedAttempts", 0),
                    locked_until=(
                        datetime.fromisoformat(item["lockedUntil"])
                        if item.get("lockedUntil")
                        else None
                    ),
                    last_attempt_at=datetime.fromisoformat(item["lastAttemptAt"]),
                    ip_addresses=item.get("ipAddresses", []),
                )

                # Log successful retrieval
                await self._log_database_operation(
                    operation="GET_ACCOUNT_LOCKOUT",
                    table_name=self.lockout_table_name,
                    record_id=person_id,
                    context=context,
                    success=True,
                    additional_data={
                        "failed_attempts": lockout.failed_attempts,
                        "is_locked": lockout.locked_until is not None
                        and lockout.locked_until > datetime.utcnow(),
                    },
                )

                return lockout
            else:
                # Log that no lockout was found
                await self._log_database_operation(
                    operation="GET_ACCOUNT_LOCKOUT",
                    table_name=self.lockout_table_name,
                    record_id=person_id,
                    context=context,
                    success=True,
                    additional_data={"found": False},
                )

            return None

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="GET_ACCOUNT_LOCKOUT",
                table_name=self.lockout_table_name,
                record_id=person_id,
                context=context,
                success=False,
                error_message=str(e),
            )

            raise self._handle_database_error("get_account_lockout", e, context)

    async def save_account_lockout(
        self, lockout_info: AccountLockout, context: Optional[ErrorContext] = None
    ):
        """Save account lockout information with audit logging"""
        if not self.lockout_table:
            self.logger.warning(
                "Lockout table not available, cannot save account lockout information"
            )
            return

        try:
            # Check if there's an existing lockout to track changes
            existing_lockout = None
            try:
                existing_lockout = await self.get_account_lockout(
                    lockout_info.person_id, context
                )
            except Exception:
                # Continue even if we can't get existing lockout
                pass

            item = {
                "personId": lockout_info.person_id,
                "failedAttempts": lockout_info.failed_attempts,
                "lastAttemptAt": lockout_info.last_attempt_at.isoformat(),
                "ipAddresses": lockout_info.ip_addresses,
            }

            if lockout_info.locked_until:
                item["lockedUntil"] = lockout_info.locked_until.isoformat()

            self.lockout_table.put_item(Item=item)

            # Log successful save
            await self._log_database_operation(
                operation="SAVE_ACCOUNT_LOCKOUT",
                table_name=self.lockout_table_name,
                record_id=lockout_info.person_id,
                context=context,
                before_state=existing_lockout.__dict__ if existing_lockout else None,
                after_state=lockout_info.__dict__,
                success=True,
                additional_data={
                    "failed_attempts": lockout_info.failed_attempts,
                    "is_locked": lockout_info.locked_until is not None
                    and lockout_info.locked_until > datetime.utcnow(),
                    "is_new_lockout": existing_lockout is None,
                },
            )

        except ClientError as e:
            # Log database error
            await self._log_database_operation(
                operation="SAVE_ACCOUNT_LOCKOUT",
                table_name=self.lockout_table_name,
                record_id=lockout_info.person_id,
                context=context,
                success=False,
                error_message=str(e),
                additional_data={"lockout_info": lockout_info.__dict__},
            )

            raise self._handle_database_error("save_account_lockout", e, context)

    async def clear_account_lockout(
        self, person_id: str, context: Optional[ErrorContext] = None
    ):
        """Clear account lockout information with audit logging"""
        if not self.lockout_table:
            self.logger.warning(
                "Lockout table not available, cannot clear account lockout information"
            )
            return

        try:
            # Get existing lockout for audit logging
            existing_lockout = None
            try:
                existing_lockout = await self.get_account_lockout(person_id, context)
            except Exception:
                # Continue even if we can't get existing lockout
                pass

            self.lockout_table.delete_item(Key={"personId": person_id})

            # Log successful clear
            await self._log_database_operation(
                operation="CLEAR_ACCOUNT_LOCKOUT",
                table_name=self.lockout_table_name,
                record_id=person_id,
                context=context,
                before_state=existing_lockout.__dict__ if existing_lockout else None,
                success=True,
                additional_data={"had_lockout": existing_lockout is not None},
            )

        except ClientError as e:
            # Don't fail if item doesn't exist
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                # Log database error
                await self._log_database_operation(
                    operation="CLEAR_ACCOUNT_LOCKOUT",
                    table_name=self.lockout_table_name,
                    record_id=person_id,
                    context=context,
                    success=False,
                    error_message=str(e),
                )

                raise self._handle_database_error("clear_account_lockout", e, context)

    # ==================== PROJECT METHODS ====================

    def create_project(
        self, project_data: ProjectCreate, created_by: str
    ) -> Dict[str, Any]:
        """Create a new project"""
        if not self.projects_table:
            raise Exception("Projects table not available")

        project_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "id": project_id,
            "name": project_data.name,
            "description": project_data.description,
            "startDate": project_data.startDate,
            "endDate": project_data.endDate,
            "maxParticipants": project_data.maxParticipants,
            "status": project_data.status.value,
            "createdBy": created_by,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }

        try:
            self.projects_table.put_item(Item=item)
            return item
        except ClientError as e:
            raise Exception(
                f"Failed to create project: {e.response['Error']['Message']}"
            )

    async def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects"""
        if not self.projects_table:
            return []

        try:
            response = self.projects_table.scan()
            return response.get("Items", [])
        except ClientError as e:
            raise Exception(f"Failed to get projects: {e.response['Error']['Message']}")

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID"""
        if not self.projects_table:
            return None

        try:
            response = self.projects_table.get_item(Key={"id": project_id})
            return response.get("Item")
        except ClientError as e:
            raise Exception(f"Failed to get project: {e.response['Error']['Message']}")

    def update_project(
        self, project_id: str, project_data: ProjectUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a project"""
        if not self.projects_table:
            return None

        # Build update expression
        update_expression = "SET updatedAt = :updated_at"
        expression_values = {":updated_at": datetime.utcnow().isoformat()}

        if project_data.name is not None:
            update_expression += ", #name = :name"
            expression_values[":name"] = project_data.name

        if project_data.description is not None:
            update_expression += ", description = :description"
            expression_values[":description"] = project_data.description

        if project_data.startDate is not None:
            update_expression += ", startDate = :start_date"
            expression_values[":start_date"] = project_data.startDate

        if project_data.endDate is not None:
            update_expression += ", endDate = :end_date"
            expression_values[":end_date"] = project_data.endDate

        if project_data.maxParticipants is not None:
            update_expression += ", maxParticipants = :max_participants"
            expression_values[":max_participants"] = project_data.maxParticipants

        if project_data.status is not None:
            update_expression += ", #status = :status"
            expression_values[":status"] = project_data.status.value

        if project_data.category is not None:
            update_expression += ", category = :category"
            expression_values[":category"] = project_data.category

        if project_data.location is not None:
            update_expression += ", #location = :location"
            expression_values[":location"] = project_data.location

        if project_data.requirements is not None:
            update_expression += ", requirements = :requirements"
            expression_values[":requirements"] = project_data.requirements

        expression_names = {}
        if project_data.name is not None:
            expression_names["#name"] = "name"
        if project_data.status is not None:
            expression_names["#status"] = "status"
        if project_data.location is not None:
            expression_names["#location"] = "location"

        try:
            response = self.projects_table.update_item(
                Key={"id": project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise Exception(
                f"Failed to update project: {e.response['Error']['Message']}"
            )

    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        if not self.projects_table:
            return False

        try:
            self.projects_table.delete_item(
                Key={"id": project_id}, ConditionExpression=Attr("id").exists()
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise Exception(
                f"Failed to delete project: {e.response['Error']['Message']}"
            )

    # ==================== SUBSCRIPTION METHODS ====================

    def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> Dict[str, Any]:
        """Create a new subscription"""
        if not self.subscriptions_table:
            raise Exception("Subscriptions table not available")

        subscription_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "id": subscription_id,
            "personId": subscription_data.personId,
            "projectId": subscription_data.projectId,
            "status": subscription_data.status.value,
            "notes": subscription_data.notes,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }

        try:
            self.subscriptions_table.put_item(Item=item)
            return item
        except ClientError as e:
            raise Exception(
                f"Failed to create subscription: {e.response['Error']['Message']}"
            )

    async def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions"""
        if not self.subscriptions_table:
            return []

        try:
            response = self.subscriptions_table.scan()
            return response.get("Items", [])
        except ClientError as e:
            raise Exception(
                f"Failed to get subscriptions: {e.response['Error']['Message']}"
            )

    def get_subscription_by_id(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get a subscription by ID"""
        if not self.subscriptions_table:
            return None

        try:
            response = self.subscriptions_table.get_item(Key={"id": subscription_id})
            return response.get("Item")
        except ClientError as e:
            raise Exception(
                f"Failed to get subscription: {e.response['Error']['Message']}"
            )

    def get_subscriptions_by_person(self, person_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a person"""
        if not self.subscriptions_table:
            return []

        try:
            response = self.subscriptions_table.scan(
                FilterExpression=Attr("personId").eq(person_id)
            )
            return response.get("Items", [])
        except ClientError as e:
            raise Exception(
                f"Failed to get person subscriptions: {e.response['Error']['Message']}"
            )

    def get_subscriptions_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all subscriptions for a project"""
        if not self.subscriptions_table:
            return []

        try:
            response = self.subscriptions_table.scan(
                FilterExpression=Attr("projectId").eq(project_id)
            )
            return response.get("Items", [])
        except ClientError as e:
            raise Exception(
                f"Failed to get project subscriptions: {e.response['Error']['Message']}"
            )

    def update_subscription(
        self, subscription_id: str, subscription_data: SubscriptionUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a subscription"""
        if not self.subscriptions_table:
            return None

        # Build update expression
        update_expression = "SET updatedAt = :updated_at"
        expression_values = {":updated_at": datetime.utcnow().isoformat()}

        if subscription_data.status is not None:
            update_expression += ", #status = :status"
            expression_values[":status"] = subscription_data.status.value

        if subscription_data.notes is not None:
            update_expression += ", notes = :notes"
            expression_values[":notes"] = subscription_data.notes

        expression_names = {}
        if subscription_data.status is not None:
            expression_names["#status"] = "status"

        try:
            response = self.subscriptions_table.update_item(
                Key={"id": subscription_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise Exception(
                f"Failed to update subscription: {e.response['Error']['Message']}"
            )

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription"""
        if not self.subscriptions_table:
            return False

        try:
            self.subscriptions_table.delete_item(
                Key={"id": subscription_id}, ConditionExpression=Attr("id").exists()
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise Exception(
                f"Failed to delete subscription: {e.response['Error']['Message']}"
            )
