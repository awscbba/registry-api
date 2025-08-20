#!/usr/bin/env python3
"""
Comprehensive Repository Pattern Diagnostic Tool

This script identifies ALL potential issues with the repository pattern migration
to prevent the frustrating cycle of discovering issues one by one.
"""

import sys
import os
import importlib.util
import ast
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


class RepositoryPatternDiagnostic:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.success_checks = []

    def log_issue(self, category, description, severity="ERROR"):
        self.issues.append(
            {"category": category, "description": description, "severity": severity}
        )

    def log_warning(self, category, description):
        self.warnings.append({"category": category, "description": description})

    def log_success(self, category, description):
        self.success_checks.append({"category": category, "description": description})

    def check_imports(self):
        """Check all import issues that could cause runtime failures"""
        print("🔍 Checking Import Issues...")

        # Check for relative imports in repository files
        repo_files = [
            "src/repositories/subscription_repository.py",
            "src/repositories/user_repository.py",
            "src/repositories/project_repository.py",
            "src/repositories/audit_repository.py",
            "src/services/subscriptions_service.py",
        ]

        for file_path in repo_files:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()
                    if "from .." in content:
                        self.log_issue(
                            "IMPORTS", f"Relative imports found in {file_path}"
                        )
                    else:
                        self.log_success(
                            "IMPORTS", f"No relative imports in {file_path}"
                        )
            else:
                self.log_issue("FILES", f"Missing file: {file_path}")

    def check_method_compatibility(self):
        """Check method name compatibility between services and repositories"""
        print("🔍 Checking Method Compatibility...")

        try:
            # Import and check base repository methods
            from repositories.base_repository import BaseRepository

            base_methods = [
                method
                for method in dir(BaseRepository)
                if not method.startswith("_")
                and callable(getattr(BaseRepository, method))
            ]

            # Check subscription repository methods
            from repositories.subscription_repository import SubscriptionRepository

            sub_repo = SubscriptionRepository()

            # Check if service is calling correct methods
            service_file = "src/services/subscriptions_service.py"
            if os.path.exists(service_file):
                with open(service_file, "r") as f:
                    content = f.read()

                # Check for incorrect method calls
                incorrect_methods = [
                    "find_all",
                    "find_by_id",
                    "find_by_project_id",
                    "find_by_email",
                ]

                for method in incorrect_methods:
                    if f".{method}(" in content:
                        self.log_issue(
                            "METHODS",
                            f"Incorrect method call '{method}' found in subscriptions_service.py",
                        )

                # Check for correct method calls
                correct_methods = [
                    "list_all",
                    "get_by_id",
                    "get_by_project_id",
                    "get_by_email",
                ]

                for method in correct_methods:
                    if f".{method}(" in content:
                        self.log_success(
                            "METHODS", f"Correct method call '{method}' found"
                        )

        except Exception as e:
            self.log_issue("METHODS", f"Failed to check method compatibility: {str(e)}")

    def check_table_names(self):
        """Check that all repositories use correct DynamoDB table names"""
        print("🔍 Checking Table Names...")

        expected_tables = {
            "SubscriptionRepository": "SubscriptionsTable",
            "UserRepository": "PeopleTable",
            "ProjectRepository": "ProjectsTable",
            "AuditRepository": "AuditLogsTable",
        }

        for repo_class, expected_table in expected_tables.items():
            try:
                # Check the repository file for table name
                repo_file = f"src/repositories/{repo_class.lower().replace('repository', '_repository')}.py"
                if os.path.exists(repo_file):
                    with open(repo_file, "r") as f:
                        content = f.read()
                        if f'table_name: str = "{expected_table}"' in content:
                            self.log_success(
                                "TABLES",
                                f"{repo_class} uses correct table name: {expected_table}",
                            )
                        elif "table_name: str =" in content:
                            # Extract the actual table name
                            import re

                            match = re.search(r'table_name: str = "([^"]+)"', content)
                            if match:
                                actual_table = match.group(1)
                                if actual_table != expected_table:
                                    self.log_issue(
                                        "TABLES",
                                        f"{repo_class} uses wrong table name: {actual_table}, expected: {expected_table}",
                                    )
                        else:
                            self.log_warning(
                                "TABLES",
                                f"Could not determine table name for {repo_class}",
                            )
                else:
                    self.log_issue("FILES", f"Repository file not found: {repo_file}")

            except Exception as e:
                self.log_issue(
                    "TABLES", f"Failed to check table name for {repo_class}: {str(e)}"
                )

    def check_runtime_imports(self):
        """Test actual runtime imports to catch import errors"""
        print("🔍 Checking Runtime Imports...")

        import_tests = [
            ("repositories.subscription_repository", "SubscriptionRepository"),
            ("repositories.user_repository", "UserRepository"),
            ("services.subscriptions_service", "SubscriptionsService"),
            ("repositories.base_repository", "BaseRepository"),
        ]

        for module_name, class_name in import_tests:
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                self.log_success(
                    "RUNTIME_IMPORTS",
                    f"Successfully imported {class_name} from {module_name}",
                )
            except Exception as e:
                self.log_issue(
                    "RUNTIME_IMPORTS",
                    f"Failed to import {class_name} from {module_name}: {str(e)}",
                )

    def check_service_instantiation(self):
        """Test that services can be instantiated without errors"""
        print("🔍 Checking Service Instantiation...")

        try:
            from services.subscriptions_service import SubscriptionsService

            service = SubscriptionsService()
            self.log_success(
                "INSTANTIATION", "SubscriptionsService instantiated successfully"
            )

            # Check repository attributes
            if hasattr(service, "subscription_repository"):
                self.log_success(
                    "INSTANTIATION", "subscription_repository attribute exists"
                )
            else:
                self.log_issue(
                    "INSTANTIATION", "subscription_repository attribute missing"
                )

            if hasattr(service, "user_repository"):
                self.log_success("INSTANTIATION", "user_repository attribute exists")
            else:
                self.log_issue("INSTANTIATION", "user_repository attribute missing")

        except Exception as e:
            self.log_issue(
                "INSTANTIATION", f"Failed to instantiate SubscriptionsService: {str(e)}"
            )
            traceback.print_exc()

    def check_environment_variables(self):
        """Check required environment variables"""
        print("🔍 Checking Environment Variables...")

        required_env_vars = [
            "SUBSCRIPTIONS_TABLE_NAME",
            "PEOPLE_TABLE_NAME",
            "PROJECTS_TABLE_NAME",
        ]

        for env_var in required_env_vars:
            if os.getenv(env_var):
                self.log_success(
                    "ENVIRONMENT", f"{env_var} is set: {os.getenv(env_var)}"
                )
            else:
                self.log_warning("ENVIRONMENT", f"{env_var} not set (using defaults)")

    def check_dependency_compatibility(self):
        """Check that all required dependencies are available"""
        print("🔍 Checking Dependencies...")

        required_packages = ["boto3", "botocore", "pydantic", "fastapi", "mangum"]

        for package in required_packages:
            try:
                importlib.import_module(package)
                self.log_success("DEPENDENCIES", f"{package} available")
            except ImportError:
                self.log_issue("DEPENDENCIES", f"{package} not available")

    def check_repository_methods(self):
        """Check that repositories have all required methods"""
        print("🔍 Checking Repository Method Availability...")

        try:
            from repositories.subscription_repository import SubscriptionRepository
            from repositories.user_repository import UserRepository

            # Check SubscriptionRepository methods
            sub_repo = SubscriptionRepository()
            required_methods = ["list_all", "get_by_id", "create", "update", "delete"]

            for method in required_methods:
                if hasattr(sub_repo, method):
                    self.log_success(
                        "REPO_METHODS", f"SubscriptionRepository has {method}"
                    )
                else:
                    self.log_issue(
                        "REPO_METHODS", f"SubscriptionRepository missing {method}"
                    )

            # Check custom methods
            if hasattr(sub_repo, "get_by_project_id"):
                self.log_success(
                    "REPO_METHODS", "SubscriptionRepository has get_by_project_id"
                )
            else:
                self.log_issue(
                    "REPO_METHODS", "SubscriptionRepository missing get_by_project_id"
                )

            # Check UserRepository methods
            user_repo = UserRepository()
            if hasattr(user_repo, "get_by_email"):
                self.log_success("REPO_METHODS", "UserRepository has get_by_email")
            else:
                self.log_issue("REPO_METHODS", "UserRepository missing get_by_email")

        except Exception as e:
            self.log_issue(
                "REPO_METHODS", f"Failed to check repository methods: {str(e)}"
            )

    def run_all_checks(self):
        """Run all diagnostic checks"""
        print("🚀 Starting Comprehensive Repository Pattern Diagnostic\n")

        self.check_imports()
        self.check_method_compatibility()
        self.check_table_names()
        self.check_runtime_imports()
        self.check_service_instantiation()
        self.check_environment_variables()
        self.check_dependency_compatibility()
        self.check_repository_methods()

        return self.generate_report()

    def generate_report(self):
        """Generate comprehensive diagnostic report"""
        print("\n" + "=" * 80)
        print("📊 REPOSITORY PATTERN DIAGNOSTIC REPORT")
        print("=" * 80)

        # Success Summary
        if self.success_checks:
            print(f"\n✅ SUCCESS CHECKS ({len(self.success_checks)}):")
            for check in self.success_checks:
                print(f"   ✅ {check['category']}: {check['description']}")

        # Warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   ⚠️  {warning['category']}: {warning['description']}")

        # Critical Issues
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   ❌ {issue['category']}: {issue['description']}")

        # Overall Status
        print(f"\n📈 OVERALL STATUS:")
        if not self.issues:
            print("   🎉 ALL CHECKS PASSED - Repository pattern should work correctly!")
            return True
        else:
            print(
                f"   💥 {len(self.issues)} CRITICAL ISSUES FOUND - These must be fixed before deployment"
            )
            return False


if __name__ == "__main__":
    diagnostic = RepositoryPatternDiagnostic()
    success = diagnostic.run_all_checks()

    if success:
        print("\n🚀 Repository pattern is ready for deployment!")
        sys.exit(0)
    else:
        print("\n🛑 Repository pattern has issues that need to be resolved!")
        sys.exit(1)
