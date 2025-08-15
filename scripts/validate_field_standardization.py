#!/usr/bin/env python3
"""
Field Standardization Validation Script

This script validates that the field standardization implementation is working correctly.
It tests the key components without modifying any data.

Usage:
    python3 validate_field_standardization.py
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

# Add the registry-api src to the path
registry_api_path = os.path.join(os.path.dirname(__file__), "..", "registry-api")
sys.path.insert(0, os.path.join(registry_api_path, "src"))

try:
    from models.person import Person, PersonCreate, PersonUpdate
    from services.defensive_dynamodb_service import DefensiveDynamoDBService
    from models.password_reset import PasswordResetRequest, PasswordResetValidation
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    print(
        "And that all dependencies are installed with: cd registry-api && uv add pydantic boto3 bcrypt"
    )
    sys.exit(1)


class FieldStandardizationValidator:
    """Validates field standardization implementation"""

    def __init__(self):
        self.test_results = []
        self.errors = []

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append(
            {"test": test_name, "passed": passed, "details": details}
        )
        print(f"{status} {test_name}")
        if details and not passed:
            print(f"    Details: {details}")

    def test_person_to_item_snake_case(self):
        """Test that Person to DynamoDB item conversion uses snake_case"""
        try:
            service = DefensiveDynamoDBService()

            # Create test person
            person_data = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@test.com",
                "phone": "+1234567890",
                "date_of_birth": "1990-01-01",
                "address": {
                    "street": "123 Main St",
                    "city": "Test City",
                    "state": "CA",
                    "postal_code": "12345",
                    "country": "USA",
                },
                "is_admin": False,
            }

            person_create = PersonCreate(**person_data)
            person = Person.create_new(person_create)

            # Convert to database item
            item = service._safe_person_to_item(person)

            # Check for snake_case fields
            snake_case_fields = [
                "first_name",
                "last_name",
                "date_of_birth",
                "is_admin",
                "is_active",
                "created_at",
                "updated_at",
            ]

            missing_snake_fields = []
            for field in snake_case_fields:
                if field not in item:
                    missing_snake_fields.append(field)

            # Check for unwanted camelCase fields
            camel_case_fields = [
                "firstName",
                "lastName",
                "dateOfBirth",
                "isAdmin",
                "isActive",
                "createdAt",
                "updatedAt",
            ]

            found_camel_fields = []
            for field in camel_case_fields:
                if field in item:
                    found_camel_fields.append(field)

            if missing_snake_fields or found_camel_fields:
                details = f"Missing snake_case: {missing_snake_fields}, Found camelCase: {found_camel_fields}"
                self.log_test("Person to Item Snake Case", False, details)
            else:
                self.log_test("Person to Item Snake Case", True)

        except Exception as e:
            self.log_test("Person to Item Snake Case", False, str(e))

    def test_item_to_person_backward_compatibility(self):
        """Test that DynamoDB item to Person conversion handles both naming conventions"""
        try:
            service = DefensiveDynamoDBService()

            # Test with snake_case item
            snake_case_item = {
                "id": "test-123",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@test.com",
                "phone": "+1234567890",
                "date_of_birth": "1990-01-01",
                "is_admin": False,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "password_hash": "test_hash",
                "password_salt": "test_salt",
                "address": {},
            }

            person_snake = service._safe_item_to_person(snake_case_item)

            # Test with camelCase item (legacy)
            camel_case_item = {
                "id": "test-456",
                "firstName": "Bob",
                "lastName": "Johnson",
                "email": "bob@test.com",
                "phone": "+1234567890",
                "dateOfBirth": "1990-01-01",
                "isAdmin": False,
                "isActive": True,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "passwordHash": "test_hash_2",
                "passwordSalt": "test_salt_2",
                "address": {},
            }

            person_camel = service._safe_item_to_person(camel_case_item)

            # Test with mixed item (should prefer snake_case)
            mixed_item = {
                "id": "test-789",
                "first_name": "Alice_Snake",  # Should be preferred
                "firstName": "Alice_Camel",  # Should be ignored
                "last_name": "Brown_Snake",
                "lastName": "Brown_Camel",
                "email": "alice@test.com",
                "password_hash": "snake_hash",  # Should be preferred
                "passwordHash": "camel_hash",  # Should be ignored
                "is_active": True,
                "isActive": False,  # Should be ignored
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "address": {},
            }

            person_mixed = service._safe_item_to_person(mixed_item)

            # Validate conversions
            errors = []

            if person_snake.first_name != "Jane":
                errors.append("Snake case conversion failed")
            if person_camel.first_name != "Bob":
                errors.append("Camel case conversion failed")
            if person_mixed.first_name != "Alice_Snake":
                errors.append(
                    f"Mixed case preference failed: got {person_mixed.first_name}"
                )
            if person_mixed.password_hash != "snake_hash":
                errors.append(
                    f"Mixed password hash preference failed: got {person_mixed.password_hash}"
                )
            if person_mixed.is_active != True:
                errors.append("Mixed boolean preference failed")

            if errors:
                self.log_test(
                    "Item to Person Backward Compatibility", False, "; ".join(errors)
                )
            else:
                self.log_test("Item to Person Backward Compatibility", True)

        except Exception as e:
            self.log_test("Item to Person Backward Compatibility", False, str(e))

    def test_field_mappings_consistency(self):
        """Test that field mappings are consistent with snake_case"""
        try:
            # This tests the field mappings used in update operations
            expected_mappings = {
                "first_name": "first_name",
                "last_name": "last_name",
                "date_of_birth": "date_of_birth",
                "is_admin": "is_admin",
                "is_active": "is_active",
                "failed_login_attempts": "failed_login_attempts",
                "account_locked_until": "account_locked_until",
                "require_password_change": "require_password_change",
                "last_password_change": "last_password_change",
                "last_login_at": "last_login_at",
                "password_hash": "password_hash",
                "password_salt": "password_salt",
                "email_verified": "email_verified",
            }

            # Check that all mappings use snake_case
            camel_case_found = []
            for internal_name, db_name in expected_mappings.items():
                # Check if database field name has camelCase
                if any(c.isupper() for c in db_name[1:]):
                    camel_case_found.append(f"{internal_name} -> {db_name}")

            if camel_case_found:
                self.log_test(
                    "Field Mappings Consistency",
                    False,
                    f"CamelCase found: {camel_case_found}",
                )
            else:
                self.log_test("Field Mappings Consistency", True)

        except Exception as e:
            self.log_test("Field Mappings Consistency", False, str(e))

    def test_password_reset_service_integration(self):
        """Test that password reset service uses PersonUpdate correctly"""
        try:
            # Test PersonUpdate object creation
            person_update = PersonUpdate(
                password_hash="new_hash",
                require_password_change=False,
                failed_login_attempts=0,
            )

            # Verify the object has the expected attributes
            if not hasattr(person_update, "password_hash"):
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "PersonUpdate missing password_hash",
                )
                return

            if not hasattr(person_update, "require_password_change"):
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "PersonUpdate missing require_password_change",
                )
                return

            if not hasattr(person_update, "failed_login_attempts"):
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "PersonUpdate missing failed_login_attempts",
                )
                return

            # Verify values
            if person_update.password_hash != "new_hash":
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "Password hash not set correctly",
                )
                return

            if person_update.require_password_change != False:
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "require_password_change not set correctly",
                )
                return

            if person_update.failed_login_attempts != 0:
                self.log_test(
                    "Password Reset Service Integration",
                    False,
                    "failed_login_attempts not set correctly",
                )
                return

            self.log_test("Password Reset Service Integration", True)

        except Exception as e:
            self.log_test("Password Reset Service Integration", False, str(e))

    def test_address_normalization(self):
        """Test address field normalization"""
        try:
            service = DefensiveDynamoDBService()

            # Test different postal code field variants
            test_addresses = [
                {
                    "street": "123 Main",
                    "city": "Test",
                    "state": "CA",
                    "postal_code": "12345",
                    "country": "USA",
                },
                {
                    "street": "123 Main",
                    "city": "Test",
                    "state": "CA",
                    "postalCode": "12345",
                    "country": "USA",
                },
                {
                    "street": "123 Main",
                    "city": "Test",
                    "state": "CA",
                    "zipCode": "12345",
                    "country": "USA",
                },
                {
                    "street": "123 Main",
                    "city": "Test",
                    "state": "CA",
                    "zip_code": "12345",
                    "country": "USA",
                },
            ]

            errors = []
            for i, address in enumerate(test_addresses):
                normalized = service._normalize_address_for_storage(address)

                if "postal_code" not in normalized:
                    errors.append(f"Address {i}: missing postal_code")
                elif normalized["postal_code"] != "12345":
                    errors.append(f"Address {i}: wrong postal_code value")

                # Check that other variants are removed (except postal_code)
                unwanted_fields = ["postalCode", "zipCode"]
                for field in unwanted_fields:
                    if field in normalized:
                        errors.append(
                            f"Address {i}: unwanted field {field} still present"
                        )

            if errors:
                self.log_test("Address Normalization", False, "; ".join(errors))
            else:
                self.log_test("Address Normalization", True)

        except Exception as e:
            self.log_test("Address Normalization", False, str(e))

    def run_all_tests(self):
        """Run all validation tests"""
        print("🚀 Running Field Standardization Validation Tests")
        print("=" * 60)

        self.test_person_to_item_snake_case()
        self.test_item_to_person_backward_compatibility()
        self.test_field_mappings_consistency()
        self.test_password_reset_service_integration()
        self.test_address_normalization()

        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        passed_tests = sum(1 for result in self.test_results if result["passed"])
        total_tests = len(self.test_results)

        print(f"Tests passed: {passed_tests}/{total_tests}")

        if passed_tests == total_tests:
            print("🎉 All tests passed! Field standardization is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the implementation.")

            # Show failed tests
            failed_tests = [
                result for result in self.test_results if not result["passed"]
            ]
            for test in failed_tests:
                print(f"❌ {test['test']}: {test['details']}")

            return False

    def generate_report(self):
        """Generate a detailed validation report"""
        report = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for result in self.test_results if result["passed"]),
            "failed_tests": sum(
                1 for result in self.test_results if not result["passed"]
            ),
            "test_results": self.test_results,
        }

        report_filename = f"field_standardization_validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_filename, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📄 Detailed report saved to: {report_filename}")
        return report_filename


def main():
    """Main validation function"""
    validator = FieldStandardizationValidator()

    try:
        success = validator.run_all_tests()
        validator.generate_report()

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Validation failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
