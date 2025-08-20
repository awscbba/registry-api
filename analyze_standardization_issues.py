#!/usr/bin/env python3
"""
Comprehensive Standardization Analysis Tool

Analyzes the current codebase for naming inconsistencies and standardization opportunities.
"""

import sys
import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


class StandardizationAnalyzer:
    def __init__(self):
        self.issues = []
        self.table_names_found = set()
        self.env_vars_found = set()
        self.hardcoded_names = []
        self.naming_patterns = {}

    def analyze_file(self, file_path: Path):
        """Analyze a single Python file for standardization issues"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find table name patterns
            self._find_table_names(file_path, content)
            self._find_env_vars(file_path, content)
            self._find_hardcoded_values(file_path, content)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _find_table_names(self, file_path: Path, content: str):
        """Find table name patterns in the file"""
        # Pattern 1: Repository constructors with default table names
        repo_pattern = r'def __init__\(.*table_name.*=.*["\']([^"\']+)["\']'
        matches = re.findall(repo_pattern, content)
        for match in matches:
            self.table_names_found.add(match)
            self.naming_patterns[match] = f"Repository default in {file_path.name}"

        # Pattern 2: Direct table references
        table_pattern = r'["\']([A-Za-z-]+[Tt]able[A-Za-z-]*)["\']'
        matches = re.findall(table_pattern, content)
        for match in matches:
            if "table" in match.lower():
                self.table_names_found.add(match)
                self.naming_patterns[match] = f"Direct reference in {file_path.name}"

        # Pattern 3: DynamoDB Table() calls
        dynamodb_pattern = r'Table\(["\']([^"\']+)["\']'
        matches = re.findall(dynamodb_pattern, content)
        for match in matches:
            self.table_names_found.add(match)
            self.hardcoded_names.append((file_path, match, "DynamoDB Table() call"))

    def _find_env_vars(self, file_path: Path, content: str):
        """Find environment variable usage"""
        # Pattern 1: os.getenv() calls
        getenv_pattern = r'os\.getenv\(["\']([^"\']+)["\']'
        matches = re.findall(getenv_pattern, content)
        for match in matches:
            self.env_vars_found.add(match)

        # Pattern 2: os.environ.get() calls
        environ_pattern = r'os\.environ\.get\(["\']([^"\']+)["\']'
        matches = re.findall(environ_pattern, content)
        for match in matches:
            self.env_vars_found.add(match)

    def _find_hardcoded_values(self, file_path: Path, content: str):
        """Find hardcoded values that should be configurable"""
        # Look for people-registry patterns
        registry_pattern = r'["\']people-registry[^"\']*["\']'
        matches = re.findall(registry_pattern, content)
        for match in matches:
            self.hardcoded_names.append(
                (file_path, match.strip("\"'"), "Hardcoded registry name")
            )

    def analyze_codebase(self):
        """Analyze the entire codebase"""
        print("🔍 Analyzing codebase for standardization issues...")

        # Analyze Python files in src/
        src_path = Path("src")
        if src_path.exists():
            for py_file in src_path.rglob("*.py"):
                self.analyze_file(py_file)

        # Analyze infrastructure files
        infra_path = Path("../registry-infrastructure")
        if infra_path.exists():
            for py_file in infra_path.rglob("*.py"):
                if "site-packages" not in str(py_file):  # Skip dependencies
                    self.analyze_file(py_file)

    def get_actual_aws_tables(self):
        """Get actual table names from AWS"""
        try:
            import boto3

            dynamodb = boto3.client("dynamodb")
            response = dynamodb.list_tables()
            return set(response["TableNames"])
        except Exception as e:
            print(f"⚠️  Could not fetch AWS tables: {e}")
            return set()

    def analyze_naming_patterns(self):
        """Analyze naming patterns and identify inconsistencies"""
        patterns = {"PascalCase": [], "kebab-case": [], "snake_case": [], "mixed": []}

        for name in self.table_names_found:
            if re.match(r"^[A-Z][a-zA-Z]*Table$", name):
                patterns["PascalCase"].append(name)
            elif "-" in name:
                patterns["kebab-case"].append(name)
            elif "_" in name:
                patterns["snake_case"].append(name)
            else:
                patterns["mixed"].append(name)

        return patterns

    def generate_report(self):
        """Generate comprehensive standardization report"""
        print("\n" + "=" * 80)
        print("📊 STANDARDIZATION ANALYSIS REPORT")
        print("=" * 80)

        # Get actual AWS tables
        aws_tables = self.get_actual_aws_tables()

        print(f"\n🗄️  ACTUAL AWS TABLES ({len(aws_tables)}):")
        for table in sorted(aws_tables):
            print(f"   📋 {table}")

        print(f"\n🔍 FOUND TABLE REFERENCES IN CODE ({len(self.table_names_found)}):")
        for table in sorted(self.table_names_found):
            source = self.naming_patterns.get(table, "Unknown source")
            in_aws = "✅" if table in aws_tables else "❌"
            print(f"   {in_aws} {table} ({source})")

        print(f"\n🌍 ENVIRONMENT VARIABLES USED ({len(self.env_vars_found)}):")
        for env_var in sorted(self.env_vars_found):
            print(f"   🔧 {env_var}")

        print(f"\n⚠️  HARDCODED VALUES FOUND ({len(self.hardcoded_names)}):")
        for file_path, value, context in self.hardcoded_names:
            print(f"   🔒 {value} in {file_path.name} ({context})")

        # Analyze naming patterns
        patterns = self.analyze_naming_patterns()
        print(f"\n📝 NAMING PATTERN ANALYSIS:")
        for pattern_type, names in patterns.items():
            if names:
                print(f"   {pattern_type}: {len(names)} tables")
                for name in names:
                    print(f"      - {name}")

        # Identify inconsistencies
        print(f"\n🚨 IDENTIFIED ISSUES:")

        # Issue 1: Multiple naming patterns
        active_patterns = [k for k, v in patterns.items() if v]
        if len(active_patterns) > 1:
            print(
                f"   ❌ Multiple naming patterns in use: {', '.join(active_patterns)}"
            )

        # Issue 2: Tables referenced in code but not in AWS
        missing_tables = self.table_names_found - aws_tables
        if missing_tables:
            print(f"   ❌ Tables referenced in code but not found in AWS:")
            for table in missing_tables:
                print(f"      - {table}")

        # Issue 3: Hardcoded table names
        if self.hardcoded_names:
            print(f"   ❌ {len(self.hardcoded_names)} hardcoded table references found")

        # Issue 4: Inconsistent environment variable usage
        table_env_vars = [var for var in self.env_vars_found if "TABLE" in var]
        if len(table_env_vars) < len(aws_tables):
            print(f"   ❌ Not all tables have corresponding environment variables")
            print(f"      Tables: {len(aws_tables)}, Env vars: {len(table_env_vars)}")

        print(f"\n💡 RECOMMENDATIONS:")
        print("   1. Standardize on PascalCase for table names (matches AWS)")
        print("   2. Use environment variables for all table references")
        print("   3. Remove hardcoded table names from code")
        print("   4. Update infrastructure to set all required env vars")
        print("   5. Create table name validation in health checks")

        return {
            "aws_tables": aws_tables,
            "code_tables": self.table_names_found,
            "env_vars": self.env_vars_found,
            "hardcoded": self.hardcoded_names,
            "patterns": patterns,
        }


if __name__ == "__main__":
    analyzer = StandardizationAnalyzer()
    analyzer.analyze_codebase()
    results = analyzer.generate_report()

    # Exit with error code if issues found
    issues_count = len(results["hardcoded"]) + len(
        results["code_tables"] - results["aws_tables"]
    )
    if issues_count > 0:
        print(f"\n🚨 Found {issues_count} standardization issues that need attention!")
        sys.exit(1)
    else:
        print(f"\n✅ No critical standardization issues found!")
        sys.exit(0)
