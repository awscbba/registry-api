# People Register API Documentation

## Overview

This document provides comprehensive documentation for the People Register API, including all endpoints, request/response formats, error handling, and HTTP status codes.

## Base URL

```
https://api.example.com/v1
```

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Response Format

All API responses follow a consistent format with camelCase field naming:

### Success Response Format

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "createdAt": "2025-01-22T10:30:00Z",
  "updatedAt": "2025-01-22T10:30:00Z"
}
```

### Error Response Format

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": [
    {
      "field": "fieldName",
      "message": "Field-specific error message",
      "code": "VALIDATION_ERROR_CODE"
    }
  ],
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

## HTTP Status Codes

The API uses standard HTTP status codes:

- **200 OK**: Successful GET requests
- **201 Created**: Successful POST requests that create resources
- **204 No Content**: Successful DELETE requests
- **400 Bad Request**: Validation errors or malformed requests
- **401 Unauthorized**: Authentication required or failed
- **403 Forbidden**: Insufficient permissions or account locked
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflicts (e.g., duplicate email)
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected server errors

## Endpoints

### Health Check

#### GET /health

Check the health status of the API service.

**Authentication:** Not required

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "people-register-api",
  "timestamp": "2025-01-22T10:30:00Z",
  "version": "1.0.0"
}
```

### Authentication

#### POST /auth/login

Authenticate user credentials and return JWT tokens.

**Authentication:** Not required

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response (200 OK):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "expiresIn": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe"
  }
}
```

**Error Responses:**

**401 Unauthorized - Invalid credentials:**
```json
{
  "error": "AUTHENTICATION_FAILED",
  "message": "Invalid email or password",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

**403 Forbidden - Account locked:**
```json
{
  "error": "ACCOUNT_LOCKED",
  "message": "Account is locked due to too many failed login attempts",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

**429 Too Many Requests - Rate limit exceeded:**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many login attempts. Please try again later.",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

#### GET /auth/me

Get information about the currently authenticated user.

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "requirePasswordChange": false,
  "isActive": true,
  "lastLoginAt": "2025-01-22T10:30:00Z"
}
```

### Password Management

#### PUT /auth/password

Update the password for the currently authenticated user.

**Authentication:** Required

**Request Body:**
```json
{
  "currentPassword": "oldPassword123!",
  "newPassword": "newSecurePassword456!",
  "confirmPassword": "newSecurePassword456!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Password updated successfully",
  "requireReauth": true
}
```

**Error Responses:**

**400 Bad Request - Invalid current password:**
```json
{
  "error": "INVALID_CURRENT_PASSWORD",
  "message": "Current password is incorrect",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

**400 Bad Request - Password policy violation:**
```json
{
  "error": "PASSWORD_POLICY_VIOLATION",
  "message": "Password must be at least 8 characters with uppercase, lowercase, number, and special character",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_123456789"
}
```

### People Management

#### GET /people

Get a paginated list of all registered people.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Maximum number of results (1-1000, default: 100)

**Response (200 OK):**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-0123",
    "dateOfBirth": "1990-01-15",
    "address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "CA",
      "zipCode": "12345",
      "country": "USA"
    },
    "createdAt": "2025-01-20T10:30:00Z",
    "updatedAt": "2025-01-22T10:30:00Z",
    "isActive": true,
    "emailVerified": true
  }
]
```

#### GET /people/{personId}

Get detailed information for a specific person by ID.

**Authentication:** Required

**Path Parameters:**
- `personId`: UUID of the person

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-0123",
  "dateOfBirth": "1990-01-15",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zipCode": "12345",
    "country": "USA"
  },
  "createdAt": "2025-01-20T10:30:00Z",
  "updatedAt": "2025-01-22T10:30:00Z",
  "isActive": true,
  "emailVerified": true
}
```

**Error Responses:**

**404 Not Found:**
```json
{
  "error": "PERSON_NOT_FOUND",
  "message": "Person not found",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_get_notfound_1642857000"
}
```

#### POST /people

Register a new person in the system.

**Authentication:** Required

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-0123",
  "dateOfBirth": "1990-01-15",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zipCode": "12345",
    "country": "USA"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1-555-0123",
  "dateOfBirth": "1990-01-15",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zipCode": "12345",
    "country": "USA"
  },
  "createdAt": "2025-01-22T10:30:00Z",
  "updatedAt": "2025-01-22T10:30:00Z",
  "isActive": true,
  "emailVerified": false
}
```

**Error Responses:**

**400 Bad Request - Validation errors:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "The request contains invalid data",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format",
      "code": "EMAIL_FORMAT"
    },
    {
      "field": "phone",
      "message": "Invalid phone number format",
      "code": "PHONE_FORMAT"
    }
  ],
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_create_1642857000"
}
```

**409 Conflict - Email already exists:**
```json
{
  "error": "EMAIL_ALREADY_EXISTS",
  "message": "A person with this email address already exists",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_create_1642857000"
}
```

#### PUT /people/{personId}

Update an existing person with enhanced validation.

**Authentication:** Required

**Path Parameters:**
- `personId`: UUID of the person

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Smith",
  "phone": "+1-555-0124"
}
```

**Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "firstName": "John",
  "lastName": "Smith",
  "email": "john.doe@example.com",
  "phone": "+1-555-0124",
  "dateOfBirth": "1990-01-15",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zipCode": "12345",
    "country": "USA"
  },
  "createdAt": "2025-01-20T10:30:00Z",
  "updatedAt": "2025-01-22T10:30:00Z",
  "isActive": true,
  "emailVerified": true
}
```

#### DELETE /people/{personId}

Delete a person with referential integrity checks.

**Authentication:** Required

**Path Parameters:**
- `personId`: UUID of the person

**Request Body:**
```json
{
  "confirmationToken": "token_from_initiate_request",
  "reason": "User requested account deletion"
}
```

**Response (204 No Content):**
No response body.

**Error Responses:**

**400 Bad Request - Referential integrity violation:**
```json
{
  "error": "REFERENTIAL_INTEGRITY_VIOLATION",
  "message": "Cannot delete person with active subscriptions",
  "constraintType": "subscriptions",
  "relatedRecords": [
    {
      "id": "sub_123",
      "projectId": "proj_456",
      "status": "active"
    }
  ],
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_delete_1642857000"
}
```

### Search

#### GET /people/search

Search for people with filtering and pagination.

**Authentication:** Required

**Query Parameters:**
- `email` (optional): Search by email address
- `firstName` (optional): Search by first name
- `lastName` (optional): Search by last name
- `phone` (optional): Search by phone number
- `isActive` (optional): Filter by active status
- `emailVerified` (optional): Filter by email verification status
- `limit` (optional): Maximum number of results (1-1000, default: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Response (200 OK):**
```json
{
  "people": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "firstName": "John",
      "lastName": "Doe",
      "email": "john.doe@example.com",
      "phone": "+1-555-0123",
      "dateOfBirth": "1990-01-15",
      "address": {
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zipCode": "12345",
        "country": "USA"
      },
      "createdAt": "2025-01-20T10:30:00Z",
      "updatedAt": "2025-01-22T10:30:00Z",
      "isActive": true,
      "emailVerified": true
    }
  ],
  "totalCount": 1,
  "page": 1,
  "pageSize": 100,
  "hasMore": false
}
```

### Admin Functions

#### POST /people/{personId}/unlock

Unlock a locked user account (admin only).

**Authentication:** Required (Admin privileges)

**Path Parameters:**
- `personId`: UUID of the person

**Request Body:**
```json
{
  "reason": "Administrative unlock requested by support"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Account unlocked successfully. Reason: Administrative unlock requested by support",
  "unlockedAt": "2025-01-22T10:30:00Z"
}
```

**Error Responses:**

**403 Forbidden - Insufficient privileges:**
```json
{
  "error": "INSUFFICIENT_PRIVILEGES",
  "message": "Admin privileges required to unlock accounts",
  "timestamp": "2025-01-22T10:30:00Z",
  "requestId": "req_unlock_1642857000"
}
```

## Error Codes

### Authentication Errors
- `AUTHENTICATION_FAILED`: Invalid credentials
- `AUTHENTICATION_REQUIRED`: Valid token required
- `ACCOUNT_LOCKED`: Account locked due to failed attempts
- `PASSWORD_CHANGE_REQUIRED`: Password change required

### Validation Errors
- `VALIDATION_ERROR`: General validation error
- `EMAIL_FORMAT`: Invalid email format
- `PHONE_FORMAT`: Invalid phone format
- `DATE_FORMAT`: Invalid date format
- `EMAIL_ALREADY_EXISTS`: Email address already in use

### Password Errors
- `INVALID_CURRENT_PASSWORD`: Current password incorrect
- `PASSWORD_POLICY_VIOLATION`: Password doesn't meet policy
- `PASSWORD_RECENTLY_USED`: Password was recently used

### Resource Errors
- `PERSON_NOT_FOUND`: Person not found
- `REFERENTIAL_INTEGRITY_VIOLATION`: Cannot delete due to constraints

### System Errors
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_SERVER_ERROR`: Unexpected server error

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Login attempts**: 5 attempts per minute per IP
- **Password changes**: 3 attempts per hour per user
- **General API calls**: 1000 requests per hour per user

When rate limits are exceeded, the API returns a 429 status code with retry information.

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Account Lockout**: Automatic lockout after failed login attempts
- **Password Policy**: Strong password requirements
- **Audit Logging**: Comprehensive logging of all operations
- **Rate Limiting**: Protection against abuse and brute force attacks
- **Data Protection**: Sensitive fields excluded from responses

## Field Naming Convention

All API responses use camelCase field naming for consistency with frontend JavaScript conventions:

- `firstName` instead of `first_name`
- `lastName` instead of `last_name`
- `dateOfBirth` instead of `date_of_birth`
- `createdAt` instead of `created_at`
- `updatedAt` instead of `updated_at`
- `isActive` instead of `is_active`
- `emailVerified` instead of `email_verified`

This ensures seamless integration with JavaScript frontends without the need for field name transformation.