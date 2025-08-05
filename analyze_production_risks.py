#!/usr/bin/env python3
"""
Systematic Production Risk Analysis Tool

This tool analyzes the codebase for potential production issues that could cause
runtime errors, similar to the DynamoDB ExpressionAttributeNames issue we found.
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json


class ProductionRiskAnalyzer:
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.risks = []

    def analyze_all(self) -> Dict[str, List[Dict]]:
        """Run all risk analysis checks"""
        print("🔍 Starting systematic production risk analysis...")

        results = {
            "dynamodb_parameter_issues": self.analyze_dynamodb_parameters(),
            "async_await_mismatches": self.analyze_async_await_patterns(),
            "none_attribute_access": self.analyze_none_attribute_access(),
            "empty_parameter_issues": self.analyze_empty_parameters(),
            "mock_return_value_issues": self.analyze_mock_patterns(),
            "exception_handling_gaps": self.analyze_exception_handling(),
            "type_conversion_issues": self.analyze_type_conversions(),
            "conditional_parameter_issues": self.analyze_conditional_parameters(),
        }

        return results

    def analyze_dynamodb_parameters(self) -> List[Dict]:
        """Analyze DynamoDB parameter patterns for potential issues"""
        print("📊 Analyzing DynamoDB parameter patterns...")
        issues = []

        # Pattern 1: ExpressionAttributeNames with if/else
        pattern1 = r"ExpressionAttributeNames\s*=\s*(\w+)\s+if\s+\1\s+else\s+None"

        # Pattern 2: Empty dictionary assignments
        pattern2 = r"(\w+)\s*=\s*\{\}"

        # Pattern 3: Conditional DynamoDB parameters
        pattern3 = r"(ExpressionAttributeNames|ExpressionAttributeValues|ConditionExpression|FilterExpression)\s*=.*if.*else"

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text()

            # Check for problematic patterns
            for match in re.finditer(pattern1, content, re.MULTILINE):
                issues.append(
                    {
                        "file": str(py_file),
                        "type": "dynamodb_expression_names",
                        "line": content[: match.start()].count("\n") + 1,
                        "pattern": match.group(0),
                        "risk": "HIGH",
                        "description": "ExpressionAttributeNames conditional may pass empty dict to DynamoDB",
                    }
                )

            for match in re.finditer(pattern3, content, re.MULTILINE):
                issues.append(
                    {
                        "file": str(py_file),
                        "type": "dynamodb_conditional_param",
                        "line": content[: match.start()].count("\n") + 1,
                        "pattern": match.group(0),
                        "risk": "MEDIUM",
                        "description": "DynamoDB parameter with conditional assignment - verify empty handling",
                    }
                )

        return issues

    def analyze_async_await_patterns(self) -> List[Dict]:
        """Analyze async/await patterns for mismatches"""
        print("⚡ Analyzing async/await patterns...")
        issues = []

        # Pattern 1: Calling async methods without await
        async_method_pattern = r"(\w+)\.(\w+)\("

        # Pattern 2: Mock return_value with async methods
        mock_async_pattern = r"(\w+)\.(\w+)\.return_value\s*="

        for py_file in self.src_path.rglob("*.py"):
            if "test" in str(py_file):
                continue  # Skip test files for now

            content = py_file.read_text()
            lines = content.split("\n")

            # Look for potential async method calls without await
            for i, line in enumerate(lines):
                # Skip comments and strings
                if line.strip().startswith("#") or '"""' in line or "'''" in line:
                    continue

                # Look for database service calls
                if "db_service." in line and "await" not in line and "=" in line:
                    # Check if it's an async method call
                    method_match = re.search(r"db_service\.(\w+)\(", line)
                    if method_match:
                        method_name = method_match.group(1)
                        # Known async methods
                        async_methods = [
                            "get_person",
                            "create_person",
                            "update_person",
                            "delete_person",
                            "get_project_by_id",
                            "create_project",
                            "update_project",
                            "delete_project",
                            "get_subscription_by_id",
                            "create_subscription",
                            "update_subscription",
                            "delete_subscription",
                            "get_subscriptions_by_person",
                            "get_subscriptions_by_project",
                            "get_all_projects",
                            "get_all_subscriptions",
                        ]

                        if method_name in async_methods:
                            issues.append(
                                {
                                    "file": str(py_file),
                                    "type": "missing_await",
                                    "line": i + 1,
                                    "pattern": line.strip(),
                                    "risk": "HIGH",
                                    "description": f"Async method '{method_name}' called without await",
                                }
                            )

        return issues

    def analyze_none_attribute_access(self) -> List[Dict]:
        """Analyze potential None attribute access issues"""
        print("🚫 Analyzing None attribute access patterns...")
        issues = []

        # Pattern 1: Direct attribute access without None check
        attr_access_pattern = r"(\w+)\.(\w+)\.(\w+)"

        # Pattern 2: Method chaining that could fail
        chain_pattern = r"(\w+)\.get\([^)]+\)\.(\w+)"

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines):
                # Look for .get().something patterns
                for match in re.finditer(chain_pattern, line):
                    issues.append(
                        {
                            "file": str(py_file),
                            "type": "none_attribute_access",
                            "line": i + 1,
                            "pattern": match.group(0),
                            "risk": "MEDIUM",
                            "description": "Potential None attribute access after .get() call",
                        }
                    )

        return issues

    def analyze_empty_parameters(self) -> List[Dict]:
        """Analyze empty parameter handling"""
        print("📝 Analyzing empty parameter handling...")
        issues = []

        # Look for functions that might not handle empty parameters well
        empty_dict_pattern = r'if\s+(\w+)\s*:\s*.*\[\s*["\'](\w+)["\']\s*\]\s*=\s*\1'

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text()

            # Look for empty dictionary checks
            if "if expression_names:" in content or "if expression_values:" in content:
                # This is good - conditional parameter building
                continue

            # Look for problematic patterns
            for match in re.finditer(r"(\w+)\s+if\s+\1\s+else\s+None", content):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    {
                        "file": str(py_file),
                        "type": "conditional_none_assignment",
                        "line": line_num,
                        "pattern": match.group(0),
                        "risk": "MEDIUM",
                        "description": "Conditional None assignment - verify empty dict handling",
                    }
                )

        return issues

    def analyze_mock_patterns(self) -> List[Dict]:
        """Analyze test mock patterns for async issues"""
        print("🧪 Analyzing mock patterns...")
        issues = []

        for py_file in self.src_path.rglob("test*.py"):
            content = py_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines):
                # Look for Mock().return_value with async methods
                if "Mock(" in line and "return_value" in line:
                    # Check if it's for an async method
                    async_methods = [
                        "get_person",
                        "create_person",
                        "update_person",
                        "delete_person",
                        "get_project_by_id",
                        "create_project",
                        "update_project",
                        "delete_project",
                    ]

                    for method in async_methods:
                        if method in line:
                            issues.append(
                                {
                                    "file": str(py_file),
                                    "type": "mock_async_method",
                                    "line": i + 1,
                                    "pattern": line.strip(),
                                    "risk": "HIGH",
                                    "description": f"Mock for async method '{method}' should use AsyncMock",
                                }
                            )

        return issues

    def analyze_exception_handling(self) -> List[Dict]:
        """Analyze exception handling patterns"""
        print("⚠️ Analyzing exception handling...")
        issues = []

        for py_file in self.src_path.rglob("*.py"):
            if "test" in str(py_file):
                continue

            content = py_file.read_text()

            # Look for bare except clauses
            bare_except_pattern = r"except\s*:"
            for match in re.finditer(bare_except_pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    {
                        "file": str(py_file),
                        "type": "bare_except",
                        "line": line_num,
                        "pattern": "except:",
                        "risk": "MEDIUM",
                        "description": "Bare except clause may hide important errors",
                    }
                )

            # Look for missing exception handling around database calls
            db_call_pattern = r"(db_service\.\w+\(|table\.\w+\()"
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if re.search(db_call_pattern, line):
                    # Check if it's in a try block
                    try_found = False
                    for j in range(max(0, i - 10), i):
                        if "try:" in lines[j]:
                            try_found = True
                            break

                    if not try_found:
                        issues.append(
                            {
                                "file": str(py_file),
                                "type": "missing_exception_handling",
                                "line": i + 1,
                                "pattern": line.strip(),
                                "risk": "MEDIUM",
                                "description": "Database call without exception handling",
                            }
                        )

        return issues

    def analyze_type_conversions(self) -> List[Dict]:
        """Analyze type conversion issues"""
        print("🔄 Analyzing type conversions...")
        issues = []

        # Look for potential type conversion issues
        conversion_patterns = [
            r"str\([^)]*\)",
            r"int\([^)]*\)",
            r"float\([^)]*\)",
            r"dict\([^)]*\)",
            r"list\([^)]*\)",
        ]

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text()

            for pattern in conversion_patterns:
                for match in re.finditer(pattern, content):
                    line_num = content[: match.start()].count("\n") + 1
                    # Only flag if not in a try block or without None check
                    context_start = max(0, match.start() - 100)
                    context = content[context_start : match.end() + 100]

                    if "try:" not in context and "if" not in context:
                        issues.append(
                            {
                                "file": str(py_file),
                                "type": "unsafe_type_conversion",
                                "line": line_num,
                                "pattern": match.group(0),
                                "risk": "LOW",
                                "description": "Type conversion without error handling or None check",
                            }
                        )

        return issues

    def analyze_conditional_parameters(self) -> List[Dict]:
        """Analyze conditional parameter patterns"""
        print("🔀 Analyzing conditional parameters...")
        issues = []

        # Look for conditional parameter assignments that might be problematic
        conditional_patterns = [
            r"(\w+)\s*=\s*(\w+)\s+if\s+\2\s+else\s+None",
            r"(\w+)\s*=\s*(\w+)\s+if\s+\w+\s+else\s+\{\}",
            r"(\w+)\s*=\s*(\w+)\s+if\s+\w+\s+else\s+\[\]",
        ]

        for py_file in self.src_path.rglob("*.py"):
            content = py_file.read_text()

            for pattern in conditional_patterns:
                for match in re.finditer(pattern, content):
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append(
                        {
                            "file": str(py_file),
                            "type": "conditional_parameter",
                            "line": line_num,
                            "pattern": match.group(0),
                            "risk": "LOW",
                            "description": "Conditional parameter assignment - verify empty value handling",
                        }
                    )

        return issues

    def generate_report(self, results: Dict[str, List[Dict]]) -> str:
        """Generate a comprehensive risk analysis report"""
        report = []
        report.append("# Production Risk Analysis Report")
        report.append("=" * 50)
        report.append("")

        total_issues = sum(len(issues) for issues in results.values())
        high_risk = sum(
            1
            for issues in results.values()
            for issue in issues
            if issue.get("risk") == "HIGH"
        )
        medium_risk = sum(
            1
            for issues in results.values()
            for issue in issues
            if issue.get("risk") == "MEDIUM"
        )
        low_risk = sum(
            1
            for issues in results.values()
            for issue in issues
            if issue.get("risk") == "LOW"
        )

        report.append(f"## Summary")
        report.append(f"- **Total Issues Found**: {total_issues}")
        report.append(f"- **High Risk**: {high_risk}")
        report.append(f"- **Medium Risk**: {medium_risk}")
        report.append(f"- **Low Risk**: {low_risk}")
        report.append("")

        for category, issues in results.items():
            if not issues:
                continue

            report.append(f"## {category.replace('_', ' ').title()}")
            report.append(f"Found {len(issues)} potential issues:")
            report.append("")

            for issue in issues:
                risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                    issue["risk"], "⚪"
                )
                report.append(
                    f"### {risk_emoji} {issue['type']} - {issue['risk']} Risk"
                )
                report.append(f"- **File**: `{issue['file']}`")
                report.append(f"- **Line**: {issue['line']}")
                report.append(f"- **Pattern**: `{issue['pattern']}`")
                report.append(f"- **Description**: {issue['description']}")
                report.append("")

        return "\n".join(report)


def main():
    analyzer = ProductionRiskAnalyzer()
    results = analyzer.analyze_all()

    # Generate report
    report = analyzer.generate_report(results)

    # Save report
    with open("PRODUCTION_RISK_ANALYSIS.md", "w") as f:
        f.write(report)

    # Also save as JSON for programmatic access
    with open("production_risks.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 50)
    print("📊 Analysis Complete!")
    print(f"📄 Report saved to: PRODUCTION_RISK_ANALYSIS.md")
    print(f"📋 JSON data saved to: production_risks.json")

    # Print summary
    total_issues = sum(len(issues) for issues in results.values())
    high_risk = sum(
        1
        for issues in results.values()
        for issue in issues
        if issue.get("risk") == "HIGH"
    )

    if high_risk > 0:
        print(f"🔴 {high_risk} HIGH RISK issues found - immediate attention required!")
    elif total_issues > 0:
        print(f"🟡 {total_issues} potential issues found - review recommended")
    else:
        print("✅ No major issues detected!")


if __name__ == "__main__":
    main()
