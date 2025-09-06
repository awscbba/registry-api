"""Tests for Base Exceptions - Error handling"""

import pytest
from src.exceptions.base_exceptions import (
    BusinessLogicException,
    DatabaseException,
    AuthenticationException,
    ErrorCode,
)


class TestBaseExceptions:
    """Test Base Exception functionality"""

    def test_authentication_exception_creation(self):
        """Test AuthenticationException creation"""
        # Arrange
        message = "Invalid credentials"
        error_code = ErrorCode.AUTHENTICATION_FAILED

        # Act
        exception = AuthenticationException(message=message, error_code=error_code)

        # Assert
        assert str(exception) == message
        assert exception.error_code == error_code
        assert exception.message == message

    def test_database_exception_creation(self):
        """Test DatabaseException creation"""
        # Arrange
        message = "Database connection failed"
        operation = "get_item"

        # Act
        exception = DatabaseException(message=message, operation=operation)

        # Assert
        assert str(exception) == message
        assert exception.operation == operation

    def test_business_logic_exception_creation(self):
        """Test BusinessLogicException creation"""
        # Arrange
        message = "Business rule violated"
        error_code = ErrorCode.INVALID_INPUT

        # Act
        exception = BusinessLogicException(message=message, error_code=error_code)

        # Assert
        assert str(exception) == message
        assert exception.error_code == error_code

    def test_error_code_values(self):
        """Test ErrorCode enum values"""
        # Assert
        assert ErrorCode.AUTHENTICATION_FAILED.value == "AUTH_1001"
        assert ErrorCode.INVALID_INPUT.value == "VAL_3001"
        assert ErrorCode.INTERNAL_ERROR.value == "SYS_5004"

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy"""
        # Arrange & Act
        auth_exception = AuthenticationException(
            "Test", ErrorCode.AUTHENTICATION_FAILED
        )
        database_exception = DatabaseException("Test", "operation")
        business_exception = BusinessLogicException("Test", ErrorCode.INVALID_INPUT)

        # Assert
        assert isinstance(auth_exception, Exception)
        assert isinstance(database_exception, Exception)
        assert isinstance(business_exception, Exception)
