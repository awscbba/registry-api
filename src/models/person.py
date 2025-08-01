from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator, field_validator
import uuid
import re
from enum import Enum


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str = Field(alias="zipCode")
    country: str


class PersonBase(BaseModel):
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: EmailStr
    phone: str
    date_of_birth: str = Field(alias="dateOfBirth")  # YYYY-MM-DD format
    address: Address
    is_admin: bool = Field(default=False, alias="isAdmin")  # Admin privilege flag


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, alias="dateOfBirth")
    address: Optional[Address] = None
    is_admin: Optional[bool] = Field(None, alias="isAdmin")  # Admin privilege flag

    # Security fields for admin operations
    failed_login_attempts: Optional[int] = Field(None, alias="failedLoginAttempts")
    account_locked_until: Optional[datetime] = Field(None, alias="accountLockedUntil")
    is_active: Optional[bool] = Field(None, alias="isActive")


class Person(PersonBase):
    id: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    password_hash: Optional[str] = Field(None, alias="password_hash")
    require_password_change: Optional[bool] = Field(
        default=False, alias="requirePasswordChange"
    )
    is_active: Optional[bool] = Field(default=True, alias="isActive")
    last_login_at: Optional[datetime] = Field(None, alias="lastLoginAt")

    # Password-related fields (optional, for authentication)
    password_hash: Optional[str] = Field(
        None, exclude=True
    )  # Never include in API responses
    password_salt: Optional[str] = Field(
        None, exclude=True
    )  # Never include in API responses
    require_password_change: bool = False
    last_password_change: Optional[datetime] = Field(None, alias="lastPasswordChange")
    password_history: List[str] = Field(
        default_factory=list, exclude=True
    )  # Never include in API responses

    # Account security fields
    failed_login_attempts: int = Field(default=0, alias="failedLoginAttempts")
    account_locked_until: Optional[datetime] = Field(None, alias="accountLockedUntil")
    last_login_at: Optional[datetime] = Field(None, alias="lastLoginAt")
    is_active: bool = Field(default=True, alias="isActive")

    # Email verification fields
    email_verified: bool = Field(default=False, alias="emailVerified")
    email_verification_token: Optional[str] = Field(
        None, exclude=True
    )  # Never include in API responses
    pending_email_change: Optional[str] = Field(None, alias="pendingEmailChange")

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @classmethod
    def create_new(cls, person_data: PersonCreate) -> "Person":
        now = datetime.utcnow()
        return cls(
            id=str(uuid.uuid4()),
            **person_data.model_dump(by_alias=True),
            created_at=now,
            updated_at=now,
        )


class PersonResponse(BaseModel):
    """Secure response model for person data - excludes sensitive security fields"""

    id: str
    firstName: str
    lastName: str
    email: str
    phone: str
    dateOfBirth: str
    address: Address
    createdAt: str
    updatedAt: str
    isActive: bool = True
    emailVerified: bool = False

    @classmethod
    def from_person(cls, person: Person) -> "PersonResponse":
        """Create PersonResponse from Person model, excluding sensitive fields"""
        return cls(
            id=person.id,
            firstName=person.first_name,
            lastName=person.last_name,
            email=person.email,
            phone=person.phone,
            dateOfBirth=person.date_of_birth,
            address=person.address,
            createdAt=person.created_at.isoformat(),
            updatedAt=person.updated_at.isoformat(),
            isActive=person.is_active,
            emailVerified=person.email_verified,
        )


class PersonAdminResponse(BaseModel):
    """Admin response model that includes additional security fields for administrative purposes"""

    id: str
    firstName: str
    lastName: str
    email: str
    phone: str
    dateOfBirth: str
    address: Address
    createdAt: str
    updatedAt: str
    requirePasswordChange: bool = False
    failedLoginAttempts: int = 0
    accountLockedUntil: Optional[str] = None
    lastLoginAt: Optional[str] = None
    isActive: bool = True
    emailVerified: bool = False
    pendingEmailChange: Optional[str] = None
    lastPasswordChange: Optional[str] = None

    @classmethod
    def from_person(cls, person: Person) -> "PersonAdminResponse":
        """Create PersonAdminResponse from Person model, including security fields for admin use"""
        return cls(
            id=person.id,
            firstName=person.first_name,
            lastName=person.last_name,
            email=person.email,
            phone=person.phone,
            dateOfBirth=person.date_of_birth,
            address=person.address,
            createdAt=person.created_at.isoformat(),
            updatedAt=person.updated_at.isoformat(),
            requirePasswordChange=person.require_password_change,
            failedLoginAttempts=person.failed_login_attempts,
            accountLockedUntil=(
                person.account_locked_until.isoformat()
                if person.account_locked_until
                else None
            ),
            lastLoginAt=(
                person.last_login_at.isoformat() if person.last_login_at else None
            ),
            isActive=person.is_active,
            emailVerified=person.email_verified,
            pendingEmailChange=person.pending_email_change,
            lastPasswordChange=(
                person.last_password_change.isoformat()
                if person.last_password_change
                else None
            ),
        )


# Password Management Models
class PasswordUpdateRequest(BaseModel):
    """Request model for password updates."""

    current_password: str = Field(
        ..., min_length=1, description="Current password for verification"
    )
    new_password: str = Field(
        ..., min_length=8, description="New password meeting complexity requirements"
    )
    confirm_password: str = Field(
        ..., min_length=8, description="Confirmation of new password"
    )

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordUpdateResponse(BaseModel):
    """Response model for password update operations."""

    success: bool
    message: str
    require_reauth: bool = True  # Force re-authentication after password change


# Search Models
class PersonSearchRequest(BaseModel):
    """Request model for person search operations."""

    email: Optional[str] = Field(None, description="Search by email address")
    first_name: Optional[str] = Field(
        None, alias="firstName", description="Search by first name"
    )
    last_name: Optional[str] = Field(
        None, alias="lastName", description="Search by last name"
    )
    phone: Optional[str] = Field(None, description="Search by phone number")
    is_active: Optional[bool] = Field(
        None, alias="isActive", description="Filter by active status"
    )
    email_verified: Optional[bool] = Field(
        None, alias="emailVerified", description="Filter by email verification status"
    )
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum number of results to return"
    )
    offset: int = Field(
        default=0, ge=0, description="Number of results to skip for pagination"
    )

    class Config:
        populate_by_name = True


class PersonSearchResponse(BaseModel):
    """Response model for person search operations."""

    people: List[PersonResponse]
    total_count: int = Field(description="Total number of matching records")
    page: int = Field(description="Current page number (calculated from offset)")
    page_size: int = Field(description="Number of results per page")
    has_more: bool = Field(description="Whether there are more results available")

    @classmethod
    def create(
        cls, people: List[Person], total_count: int, limit: int, offset: int
    ) -> "PersonSearchResponse":
        """Create a search response from person list and pagination info."""
        return cls(
            people=[PersonResponse.from_person(person) for person in people],
            total_count=total_count,
            page=(offset // limit) + 1,
            page_size=limit,
            has_more=(offset + len(people)) < total_count,
        )


# Error Handling Models
class ValidationErrorType(str, Enum):
    """Types of validation errors."""

    REQUIRED_FIELD = "REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_VALUE = "INVALID_VALUE"
    DUPLICATE_VALUE = "DUPLICATE_VALUE"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    PASSWORD_POLICY = "PASSWORD_POLICY"
    EMAIL_FORMAT = "EMAIL_FORMAT"
    PHONE_FORMAT = "PHONE_FORMAT"
    DATE_FORMAT = "DATE_FORMAT"


class ValidationError(BaseModel):
    """Individual validation error details."""

    field: str = Field(description="The field that failed validation")
    message: str = Field(description="Human-readable error message")
    code: ValidationErrorType = Field(description="Machine-readable error code")
    value: Optional[str] = Field(
        None, description="The invalid value that was provided"
    )


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error: str = Field(description="Error type identifier")
    message: str = Field(description="Human-readable error message")
    details: Optional[List[ValidationError]] = Field(
        None, description="Detailed validation errors"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Email Verification Models
class EmailVerificationRequest(BaseModel):
    """Request model for email verification operations."""

    new_email: EmailStr = Field(description="New email address to verify")


class EmailVerificationResponse(BaseModel):
    """Response model for email verification operations."""

    success: bool
    message: str
    verification_sent: bool = Field(description="Whether verification emails were sent")


# Admin Models
class AdminUnlockRequest(BaseModel):
    """Request model for admin account unlock operations."""

    reason: str = Field(
        ..., min_length=10, description="Reason for unlocking the account"
    )


class AdminUnlockResponse(BaseModel):
    """Response model for admin account unlock operations."""

    success: bool
    message: str
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Deletion Models
class PersonDeletionRequest(BaseModel):
    """Request model for person deletion operations."""

    confirmation_token: str = Field(
        ..., description="Confirmation token from initial deletion request"
    )
    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for deletion"
    )


class PersonDeletionInitiateRequest(BaseModel):
    """Request model for initiating person deletion."""

    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for deletion"
    )


class PersonDeletionResponse(BaseModel):
    """Response model for person deletion operations."""

    success: bool
    message: str
    confirmation_token: Optional[str] = Field(
        None, description="Token required for final confirmation"
    )
    expires_at: Optional[datetime] = Field(
        None, description="When the confirmation token expires"
    )
    subscriptions_found: Optional[int] = Field(
        None, description="Number of active subscriptions found"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ReferentialIntegrityError(BaseModel):
    """Error model for referential integrity violations."""

    error: str = "REFERENTIAL_INTEGRITY_VIOLATION"
    message: str
    constraint_type: str = Field(
        description="Type of constraint violated (e.g., 'subscriptions')"
    )
    related_records: List[Dict[str, Any]] = Field(
        description="Details of related records preventing deletion"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
