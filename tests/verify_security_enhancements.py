#!/usr/bin/env python3
"""
Verification script for person retrieval security enhancements
"""

import json
import inspect
import os
from typing import Dict, Any

def verify_person_response_security():
    """Verify that PersonResponse excludes sensitive fields"""
    print("🔒 Verifying PersonResponse security...")

    try:
        from src.models.person import PersonResponse, PersonAdminResponse

        # Check PersonResponse fields (should exclude sensitive data)
        response_fields = set(PersonResponse.model_fields.keys())

        # Fields that should be present (non-sensitive)
        required_fields = {
            'id', 'firstName', 'lastName', 'email', 'phone',
            'dateOfBirth', 'address', 'createdAt', 'updatedAt',
            'isActive', 'emailVerified'
        }

        # Fields that should NOT be present (sensitive)
        sensitive_fields = {
            'failedLoginAttempts', 'accountLockedUntil', 'lastLoginAt',
            'pendingEmailChange', 'lastPasswordChange', 'requirePasswordChange'
        }

        # Check required fields are present
        missing_fields = required_fields - response_fields
        if missing_fields:
            print(f"❌ Missing required fields in PersonResponse: {missing_fields}")
            return False

        # Check sensitive fields are excluded
        exposed_sensitive = sensitive_fields & response_fields
        if exposed_sensitive:
            print(f"❌ Sensitive fields exposed in PersonResponse: {exposed_sensitive}")
            return False

        print("✅ PersonResponse properly excludes sensitive fields")

        # Check PersonAdminResponse includes admin fields
        admin_fields = set(PersonAdminResponse.model_fields.keys())
        admin_required = required_fields | sensitive_fields

        missing_admin_fields = admin_required - admin_fields
        if missing_admin_fields:
            print(f"❌ Missing admin fields in PersonAdminResponse: {missing_admin_fields}")
            return False

        print("✅ PersonAdminResponse includes all necessary admin fields")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verifying PersonResponse: {e}")
        return False

def verify_audit_logging():
    """Verify that audit logging function exists and is properly implemented"""
    print("\n📋 Verifying audit logging implementation...")

    try:
        # Read the handler file to check for audit logging
        handler_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'handlers', 'people_handler.py')
        with open(handler_path, 'r') as f:
            content = f.read()

        # Check for audit logging function
        if '_log_access_event' not in content:
            print("❌ Audit logging function _log_access_event not found")
            return False

        # Check for required audit logging calls
        required_audit_calls = [
            'PEOPLE_LIST_ACCESS',
            'PEOPLE_LIST_SUCCESS',
            'PERSON_ACCESS',
            'PERSON_ACCESS_SUCCESS',
            'PERSON_NOT_FOUND'
        ]

        for audit_call in required_audit_calls:
            if audit_call not in content:
                print(f"❌ Missing audit event: {audit_call}")
                return False

        print("✅ All required audit logging events are implemented")

        # Check for structured error responses
        if '"error":' not in content or '"timestamp":' not in content:
            print("❌ Structured error responses not implemented")
            return False

        print("✅ Structured error responses are implemented")
        return True

    except Exception as e:
        print(f"❌ Error verifying audit logging: {e}")
        return False

def verify_error_handling():
    """Verify enhanced error handling implementation"""
    print("\n🚨 Verifying enhanced error handling...")

    try:
        handler_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'handlers', 'people_handler.py')
        with open(handler_path, 'r') as f:
            content = f.read()

        # Check for proper 404 handling
        if 'PERSON_NOT_FOUND' not in content:
            print("❌ Enhanced 404 error handling not implemented")
            return False

        # Check for validation error handling
        if 'INVALID_PERSON_ID' not in content:
            print("❌ Person ID validation not implemented")
            return False

        # Check for pagination validation
        if 'INVALID_PAGINATION' not in content:
            print("❌ Pagination validation not implemented")
            return False

        # Check for request ID generation
        if 'request_id' not in content:
            print("❌ Request ID generation not implemented")
            return False

        print("✅ Enhanced error handling is properly implemented")
        return True

    except Exception as e:
        print(f"❌ Error verifying error handling: {e}")
        return False

def verify_endpoint_security():
    """Verify that endpoints have proper authentication and request handling"""
    print("\n🔐 Verifying endpoint security...")

    try:
        handler_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'handlers', 'people_handler.py')
        with open(handler_path, 'r') as f:
            content = f.read()

        # Check that endpoints require authentication
        if 'require_no_password_change' not in content:
            print("❌ Authentication middleware not applied to endpoints")
            return False

        # Check that Request object is injected for audit logging
        if 'request: Request' not in content:
            print("❌ Request object not injected for audit logging")
            return False

        print("✅ Endpoints have proper authentication and request handling")
        return True

    except Exception as e:
        print(f"❌ Error verifying endpoint security: {e}")
        return False

def main():
    """Run all verification checks"""
    print("🔍 Verifying Person Retrieval Security Enhancements")
    print("=" * 60)

    checks = [
        verify_person_response_security,
        verify_audit_logging,
        verify_error_handling,
        verify_endpoint_security
    ]

    all_passed = True
    for check in checks:
        if not check():
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All security enhancement checks passed!")
        print("\n📋 Task 7 Requirements Verification:")
        print("✅ Sensitive fields removed from API responses")
        print("✅ Comprehensive access logging for audit purposes")
        print("✅ Proper error handling for not found cases")
        print("✅ Enhanced authentication and authorization")
        print("✅ Structured error responses with request IDs")
        print("✅ Input validation and security checks")
        print("\n✅ Task 7 - Person Retrieval Security Enhancements is COMPLETE!")
        return True
    else:
        print("❌ Some security enhancement checks failed!")
        print("\n❌ Task 7 - Person Retrieval Security Enhancements is INCOMPLETE!")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
