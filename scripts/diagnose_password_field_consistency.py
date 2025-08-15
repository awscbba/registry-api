#!/usr/bin/env python3
"""
Password Field Consistency Diagnostic Script

This script analyzes the current state of password-related fields in the database
and code to identify inconsistencies and provide recommendations for standardization.

Usage:
    python3 diagnose_password_field_consistency.py
"""

import boto3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import re
from pathlib import Path


class PasswordFieldDiagnostic:
    def __init__(self):
        self.dynamodb = boto3.client("dynamodb", region_name="us-east-1")
        self.people_table = "PeopleTable"
        self.reset_tokens_table = "PasswordResetTokensTable"
        self.issues = []
        self.recommendations = []

    def log_issue(self, category: str, description: str, severity: str = "MEDIUM"):
        """Log an issue found during diagnosis"""
        self.issues.append(
            {
                "category": category,
                "description": description,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def log_recommendation(self, category: str, description: str, action: str):
        """Log a recommendation for fixing issues"""
        self.recommendations.append(
            {"category": category, "description": description, "action": action}
        )

    def analyze_database_schema(self):
        """Analyze the actual database schema for password-related fields"""
        print("🔍 Analyzing Database Schema...")

        try:
            # Get a sample record to analyze field names
            response = self.dynamodb.scan(
                TableName=self.people_table,
                Limit=5,
                FilterExpression="attribute_exists(email)",
            )

            if not response.get("Items"):
                self.log_issue("DATABASE", "No records found in People table", "HIGH")
                return

            # Analyze field names across all records
            all_fields = set()
            password_fields = {}
            field_variations = {}

            for item in response["Items"]:
                item_fields = set(item.keys())
                all_fields.update(item_fields)

                # Track password-related fields
                for field in item_fields:
                    if "password" in field.lower():
                        if field not in password_fields:
                            password_fields[field] = 0
                        password_fields[field] += 1

                    # Track field naming variations
                    base_field = field.lower().replace("_", "").replace("-", "")
                    if base_field not in field_variations:
                        field_variations[base_field] = []
                    if field not in field_variations[base_field]:
                        field_variations[base_field].append(field)

            print(
                f"📊 Found {len(all_fields)} unique fields across {len(response['Items'])} records"
            )
            print(f"🔐 Password-related fields: {list(password_fields.keys())}")

            # Check for field naming inconsistencies
            for base_field, variations in field_variations.items():
                if len(variations) > 1:
                    self.log_issue(
                        "FIELD_NAMING",
                        f"Multiple naming variations for '{base_field}': {variations}",
                        "HIGH",
                    )

            # Analyze specific password field issues
            if "password_hash" in password_fields and "passwordHash" in password_fields:
                self.log_issue(
                    "FIELD_NAMING",
                    "Both 'password_hash' and 'passwordHash' fields exist - major inconsistency",
                    "CRITICAL",
                )
            elif "password_hash" in password_fields:
                print("✅ Found 'password_hash' field (snake_case)")
            elif "passwordHash" in password_fields:
                print("✅ Found 'passwordHash' field (camelCase)")
            else:
                self.log_issue(
                    "MISSING_FIELD",
                    "No password hash field found in database records",
                    "CRITICAL",
                )

            return {
                "all_fields": sorted(list(all_fields)),
                "password_fields": password_fields,
                "field_variations": field_variations,
            }

        except Exception as e:
            self.log_issue(
                "DATABASE", f"Error analyzing database schema: {str(e)}", "HIGH"
            )
            return None

    def analyze_specific_user_record(
        self, email: str = "sergio.rodriguez@cbba.cloud.org.bo"
    ):
        """Analyze a specific user record in detail"""
        print(f"🔍 Analyzing specific user record: {email}")

        try:
            response = self.dynamodb.scan(
                TableName=self.people_table,
                FilterExpression="email = :email",
                ExpressionAttributeValues={":email": {"S": email}},
            )

            if not response.get("Items"):
                self.log_issue("USER_RECORD", f"User {email} not found", "HIGH")
                return None

            user_record = response["Items"][0]

            # Analyze password-related fields in detail
            password_analysis = {
                "has_password_hash_snake": "password_hash" in user_record,
                "has_password_hash_camel": "passwordHash" in user_record,
                "has_password_salt_snake": "password_salt" in user_record,
                "has_password_salt_camel": "passwordSalt" in user_record,
                "password_hash_value": None,
                "password_salt_value": None,
                "last_modified": user_record.get("updatedAt", {}).get("S", "Unknown"),
                "failed_login_attempts": user_record.get("failedLoginAttempts", {}).get(
                    "N", "0"
                ),
                "require_password_change": user_record.get(
                    "requirePasswordChange", {}
                ).get("BOOL", False),
            }

            # Get actual password hash values (for analysis, not logging)
            if "password_hash" in user_record:
                password_analysis["password_hash_value"] = (
                    user_record["password_hash"]["S"][:20] + "..."
                )
            if "passwordHash" in user_record:
                password_analysis["password_hash_value"] = (
                    user_record["passwordHash"]["S"][:20] + "..."
                )

            if "password_salt" in user_record:
                password_analysis["password_salt_value"] = user_record["password_salt"][
                    "S"
                ]
            if "passwordSalt" in user_record:
                password_analysis["password_salt_value"] = user_record["passwordSalt"][
                    "S"
                ]

            print(f"📋 Password Analysis for {email}:")
            for key, value in password_analysis.items():
                if not key.endswith("_value"):  # Don't print actual hash values
                    print(f"   {key}: {value}")

            # Check for issues
            if (
                password_analysis["has_password_hash_snake"]
                and password_analysis["has_password_hash_camel"]
            ):
                self.log_issue(
                    "USER_RECORD",
                    f"User {email} has both snake_case and camelCase password hash fields",
                    "CRITICAL",
                )
            elif (
                not password_analysis["has_password_hash_snake"]
                and not password_analysis["has_password_hash_camel"]
            ):
                self.log_issue(
                    "USER_RECORD",
                    f"User {email} has no password hash field",
                    "CRITICAL",
                )

            return password_analysis

        except Exception as e:
            self.log_issue(
                "USER_RECORD", f"Error analyzing user record: {str(e)}", "HIGH"
            )
            return None

    def analyze_code_field_mappings(self):
        """Analyze field mappings in the codebase"""
        print("🔍 Analyzing Code Field Mappings...")

        # Define paths to analyze
        api_path = Path(
            "/Users/sergio.rodriguez/Projects/Community/AWS/UserGroupCbba/CodeCatalyst/people-registry-03/registry-api"
        )

        if not api_path.exists():
            self.log_issue("CODE_ANALYSIS", "API path not found", "HIGH")
            return None

        code_analysis = {
            "field_mappings": [],
            "password_references": [],
            "update_expressions": [],
            "model_definitions": [],
        }

        # Search for field mappings
        for py_file in api_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find field mappings
                if "field_mappings" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "field_mappings" in line and "{" in line:
                            # Extract the mapping block
                            mapping_block = []
                            j = i
                            brace_count = 0
                            while j < len(lines):
                                mapping_block.append(lines[j])
                                brace_count += lines[j].count("{") - lines[j].count("}")
                                if brace_count == 0 and "{" in lines[i]:
                                    break
                                j += 1

                            code_analysis["field_mappings"].append(
                                {
                                    "file": str(py_file.relative_to(api_path)),
                                    "line": i + 1,
                                    "content": "\n".join(mapping_block),
                                }
                            )

                # Find password references
                password_patterns = [
                    r"password_hash",
                    r"passwordHash",
                    r"password_salt",
                    r"passwordSalt",
                ]

                for pattern in password_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = content.split("\n")[line_num - 1].strip()

                        code_analysis["password_references"].append(
                            {
                                "file": str(py_file.relative_to(api_path)),
                                "line": line_num,
                                "pattern": pattern,
                                "context": line_content,
                            }
                        )

                # Find update expressions
                if "update_expression_parts.append" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if (
                            "update_expression_parts.append" in line
                            and "password" in line.lower()
                        ):
                            code_analysis["update_expressions"].append(
                                {
                                    "file": str(py_file.relative_to(api_path)),
                                    "line": i + 1,
                                    "content": line.strip(),
                                }
                            )

            except Exception as e:
                self.log_issue(
                    "CODE_ANALYSIS", f"Error analyzing {py_file}: {str(e)}", "LOW"
                )

        print(f"📊 Code Analysis Results:")
        print(f"   Field mappings found: {len(code_analysis['field_mappings'])}")
        print(f"   Password references: {len(code_analysis['password_references'])}")
        print(f"   Update expressions: {len(code_analysis['update_expressions'])}")

        return code_analysis

    def analyze_password_reset_tokens(self):
        """Analyze password reset tokens table"""
        print("🔍 Analyzing Password Reset Tokens...")

        try:
            response = self.dynamodb.scan(TableName=self.reset_tokens_table, Limit=10)

            if not response.get("Items"):
                print("ℹ️ No password reset tokens found")
                return None

            tokens_analysis = {
                "total_tokens": len(response["Items"]),
                "used_tokens": 0,
                "expired_tokens": 0,
                "valid_tokens": 0,
                "field_names": set(),
            }

            current_time = datetime.utcnow()

            for token in response["Items"]:
                tokens_analysis["field_names"].update(token.keys())

                is_used = token.get("isUsed", {}).get("BOOL", False)
                expires_at_str = token.get("expiresAt", {}).get("S", "")

                if is_used:
                    tokens_analysis["used_tokens"] += 1
                elif expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(
                            expires_at_str.replace("Z", "+00:00")
                        )
                        if expires_at < current_time:
                            tokens_analysis["expired_tokens"] += 1
                        else:
                            tokens_analysis["valid_tokens"] += 1
                    except Exception:
                        pass

            print(f"📊 Token Analysis:")
            print(f"   Total tokens: {tokens_analysis['total_tokens']}")
            print(f"   Used tokens: {tokens_analysis['used_tokens']}")
            print(f"   Expired tokens: {tokens_analysis['expired_tokens']}")
            print(f"   Valid tokens: {tokens_analysis['valid_tokens']}")
            print(f"   Field names: {sorted(list(tokens_analysis['field_names']))}")

            return tokens_analysis

        except Exception as e:
            self.log_issue(
                "TOKENS", f"Error analyzing password reset tokens: {str(e)}", "MEDIUM"
            )
            return None

    def generate_standardization_recommendations(self, db_analysis, code_analysis):
        """Generate recommendations for standardizing field names"""
        print("🎯 Generating Standardization Recommendations...")

        # Determine the standard to use
        if db_analysis and "password_fields" in db_analysis:
            password_fields = db_analysis["password_fields"]

            if "password_hash" in password_fields:
                standard = "snake_case"
                standard_password_field = "password_hash"
                standard_salt_field = "password_salt"
            elif "passwordHash" in password_fields:
                standard = "camelCase"
                standard_password_field = "passwordHash"
                standard_salt_field = "passwordSalt"
            else:
                standard = "snake_case"  # Default
                standard_password_field = "password_hash"
                standard_salt_field = "password_salt"
        else:
            standard = "snake_case"  # Default
            standard_password_field = "password_hash"
            standard_salt_field = "password_salt"

        print(f"📋 Recommended Standard: {standard}")
        print(f"   Password field: {standard_password_field}")
        print(f"   Salt field: {standard_salt_field}")

        # Generate specific recommendations
        self.log_recommendation(
            "FIELD_NAMING",
            f"Standardize all password fields to {standard}",
            f"Update all code to use '{standard_password_field}' and '{standard_salt_field}'",
        )

        self.log_recommendation(
            "DATABASE_MIGRATION",
            "Migrate database records to use consistent field names",
            f"Create migration script to rename fields to {standard} format",
        )

        self.log_recommendation(
            "CODE_UPDATES",
            "Update all field mappings and update expressions",
            "Fix field_mappings dictionary and update_expression_parts in DefensiveDynamoDBService",
        )

        self.log_recommendation(
            "TESTING",
            "Create comprehensive tests for password operations",
            "Test password reset, authentication, and field updates after standardization",
        )

        return {
            "standard": standard,
            "password_field": standard_password_field,
            "salt_field": standard_salt_field,
        }

    def run_full_diagnosis(self):
        """Run complete diagnostic analysis"""
        print("🚀 Starting Password Field Consistency Diagnosis")
        print("=" * 60)

        # Run all analyses
        db_analysis = self.analyze_database_schema()
        user_analysis = self.analyze_specific_user_record()
        code_analysis = self.analyze_code_field_mappings()
        tokens_analysis = self.analyze_password_reset_tokens()

        # Generate recommendations
        standardization = self.generate_standardization_recommendations(
            db_analysis, code_analysis
        )

        # Generate report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "database_analysis": db_analysis,
            "user_analysis": user_analysis,
            "code_analysis": code_analysis,
            "tokens_analysis": tokens_analysis,
            "standardization_recommendation": standardization,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }

        # Save report
        report_file = f"password_field_diagnosis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print("\n" + "=" * 60)
        print("📊 DIAGNOSIS SUMMARY")
        print("=" * 60)

        print(f"\n🔍 Issues Found: {len(self.issues)}")
        for issue in self.issues:
            severity_emoji = {"LOW": "ℹ️", "MEDIUM": "⚠️", "HIGH": "❌", "CRITICAL": "🚨"}
            emoji = severity_emoji.get(issue["severity"], "❓")
            print(f"   {emoji} [{issue['category']}] {issue['description']}")

        print(f"\n💡 Recommendations: {len(self.recommendations)}")
        for rec in self.recommendations:
            print(f"   🎯 [{rec['category']}] {rec['description']}")
            print(f"      Action: {rec['action']}")

        print(f"\n📄 Full report saved to: {report_file}")

        return report


if __name__ == "__main__":
    diagnostic = PasswordFieldDiagnostic()
    report = diagnostic.run_full_diagnosis()
