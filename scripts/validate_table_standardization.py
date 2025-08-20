#!/usr/bin/env python3
"""
Table Standardization Validation Script

Validates that table access follows standardization guidelines.
"""

import sys
import os
import boto3
from typing import Dict, List, Set

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def get_aws_tables() -> Set[str]:
    """Get actual table names from AWS"""
    try:
        dynamodb = boto3.client("dynamodb")
        response = dynamodb.list_tables()
        return set(response["TableNames"])
    except Exception as e:
        print(f"⚠️  Could not fetch AWS tables: {e}")
        return set()


def get_required_env_vars() -> Dict[str, str]:
    """Get required environment variables and their expected values"""
    aws_tables = get_aws_tables()

    # Map environment variables to actual table names
    env_var_mapping = {
        "PEOPLE_TABLE_NAME": "PeopleTable",
        "PROJECTS_TABLE_NAME": "ProjectsTable",
        "SUBSCRIPTIONS_TABLE_NAME": "SubscriptionsTable",
        "PASSWORD_RESET_TOKENS_TABLE_NAME": "PasswordResetTokensTable",
        "AUDIT_LOGS_TABLE_NAME": "AuditLogsTable",
        "ROLES_TABLE_NAME": "people-registry-roles",  # Legacy table
        "ACCOUNT_LOCKOUT_TABLE_NAME": "AccountLockoutTable",
        "EMAIL_TRACKING_TABLE_NAME": "EmailTrackingTable",
        "PASSWORD_HISTORY_TABLE_NAME": "PasswordHistoryTable",
        "SESSION_TRACKING_TABLE_NAME": "SessionTrackingTable",
        "RATE_LIMIT_TABLE_NAME": "RateLimitTable",
        "CSRF_TOKEN_TABLE_NAME": "CSRFTokenTable",
    }

    # Filter to only include tables that actually exist
    return {
        env_var: table
        for env_var, table in env_var_mapping.items()
        if table in aws_tables
    }


def validate_environment_variables() -> bool:
    """Validate that all required environment variables are set"""
    print("🔍 Validating environment variables...")

    required_env_vars = get_required_env_vars()
    missing_vars = []
    incorrect_vars = []

    for env_var, expected_table in required_env_vars.items():
        actual_value = os.getenv(env_var)

        if actual_value is None:
            missing_vars.append(env_var)
        elif actual_value != expected_table:
            incorrect_vars.append((env_var, expected_table, actual_value))

    if missing_vars:
        print(f"❌ Missing environment variables ({len(missing_vars)}):")
        for var in missing_vars:
            print(f"   - {var}")

    if incorrect_vars:
        print(f"❌ Incorrect environment variables ({len(incorrect_vars)}):")
        for var, expected, actual in incorrect_vars:
            print(f"   - {var}: expected '{expected}', got '{actual}'")

    if not missing_vars and not incorrect_vars:
        print(
            f"✅ All {len(required_env_vars)} environment variables are correctly set"
        )
        return True

    return False


def test_service_initialization() -> bool:
    """Test that services can initialize with current configuration"""
    print("🧪 Testing service initialization...")

    services_to_test = [
        (
            "SubscriptionsService",
            "src.services.subscriptions_service",
            "SubscriptionsService",
        ),
        ("PeopleService", "src.services.people_service", "PeopleService"),
        ("RolesService", "src.services.roles_service", "RolesService"),
    ]

    failed_services = []

    for service_name, module_path, class_name in services_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            service_class = getattr(module, class_name)
            service = service_class()
            print(f"   ✅ {service_name} initialized successfully")
        except Exception as e:
            print(f"   ❌ {service_name} failed to initialize: {e}")
            failed_services.append(service_name)

    return len(failed_services) == 0


def test_repository_initialization() -> bool:
    """Test that repositories can initialize with current configuration"""
    print("🗄️  Testing repository initialization...")

    repositories_to_test = [
        ("UserRepository", "src.repositories.user_repository", "UserRepository"),
        (
            "ProjectRepository",
            "src.repositories.project_repository",
            "ProjectRepository",
        ),
        (
            "SubscriptionRepository",
            "src.repositories.subscription_repository",
            "SubscriptionRepository",
        ),
    ]

    failed_repos = []

    for repo_name, module_path, class_name in repositories_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            repo_class = getattr(module, class_name)
            repo = repo_class()
            print(f"   ✅ {repo_name} initialized successfully")
        except Exception as e:
            print(f"   ❌ {repo_name} failed to initialize: {e}")
            failed_repos.append(repo_name)

    return len(failed_repos) == 0


def validate_table_access() -> bool:
    """Validate that services can access their tables"""
    print("🔗 Validating table access...")

    aws_tables = get_aws_tables()
    required_env_vars = get_required_env_vars()

    access_failures = []

    for env_var, expected_table in required_env_vars.items():
        table_name = os.getenv(env_var, expected_table)

        if table_name not in aws_tables:
            access_failures.append((env_var, table_name))
        else:
            print(f"   ✅ {env_var} → {table_name} (exists)")

    if access_failures:
        print(f"❌ Table access failures ({len(access_failures)}):")
        for env_var, table_name in access_failures:
            print(f"   - {env_var} → {table_name} (table not found)")
        return False

    return True


def generate_summary_report():
    """Generate a summary report of standardization status"""
    print("\n" + "=" * 60)
    print("📊 STANDARDIZATION VALIDATION SUMMARY")
    print("=" * 60)

    aws_tables = get_aws_tables()
    required_env_vars = get_required_env_vars()

    print(f"\n📋 AWS Tables Found: {len(aws_tables)}")
    print(f"🔧 Required Env Vars: {len(required_env_vars)}")

    # Check naming patterns
    pascal_case_tables = [t for t in aws_tables if t[0].isupper() and "Table" in t]
    kebab_case_tables = [t for t in aws_tables if "-" in t]

    print(f"\n📝 Naming Patterns:")
    print(f"   PascalCase: {len(pascal_case_tables)} tables")
    print(f"   kebab-case: {len(kebab_case_tables)} tables")

    if kebab_case_tables:
        print(f"   Legacy tables: {', '.join(kebab_case_tables)}")

    # Environment variable coverage
    set_vars = sum(1 for var in required_env_vars.keys() if os.getenv(var))
    coverage = (set_vars / len(required_env_vars)) * 100 if required_env_vars else 0

    print(f"\n🎯 Environment Variable Coverage: {coverage:.1f}%")
    print(f"   Set: {set_vars}/{len(required_env_vars)}")


def main():
    """Main validation function"""
    print("🚀 Starting Table Standardization Validation")
    print("=" * 60)

    # Run all validations
    env_vars_ok = validate_environment_variables()
    table_access_ok = validate_table_access()
    services_ok = test_service_initialization()
    repos_ok = test_repository_initialization()

    # Generate summary
    generate_summary_report()

    # Overall result
    all_ok = env_vars_ok and table_access_ok and services_ok and repos_ok

    print(f"\n🎯 OVERALL RESULT:")
    if all_ok:
        print("✅ All standardization validations passed!")
        print("🎉 System is properly standardized")
        return 0
    else:
        print("❌ Some standardization issues found")
        print("🔧 Review the issues above and fix them")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
