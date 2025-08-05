#!/usr/bin/env python3
"""
Comprehensive analysis of systemic issues in the codebase
"""

import os
import re
import sys
from collections import defaultdict


def analyze_systemic_issues():
    """Analyze the codebase for systemic patterns that cause bugs"""

    print("🔍 SYSTEMIC CODEBASE ANALYSIS")
    print("=" * 60)

    issues = defaultdict(list)

    # Pattern 1: Unsafe .isoformat() calls
    print("\n1️⃣ Analyzing unsafe .isoformat() calls...")
    isoformat_pattern = r"\.isoformat\(\)"

    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                        lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        if re.search(isoformat_pattern, line):
                            # Check if there's a safety check
                            context = "\n".join(lines[max(0, i - 3) : i + 2])
                            if (
                                "hasattr" not in context
                                and "if.*isoformat" not in context
                            ):
                                issues["unsafe_isoformat"].append(
                                    {
                                        "file": filepath,
                                        "line": i,
                                        "code": line.strip(),
                                        "context": context,
                                    }
                                )
                except Exception as e:
                    continue

    print(
        f"   Found {len(issues['unsafe_isoformat'])} potentially unsafe .isoformat() calls"
    )

    # Pattern 2: Unsafe .value calls on enums
    print("\n2️⃣ Analyzing unsafe .value calls...")
    value_pattern = r"\.value(?!\w)"

    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                        lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        if re.search(value_pattern, line):
                            context = "\n".join(lines[max(0, i - 3) : i + 2])
                            if "hasattr" not in context and "if.*value" not in context:
                                issues["unsafe_value"].append(
                                    {
                                        "file": filepath,
                                        "line": i,
                                        "code": line.strip(),
                                        "context": context,
                                    }
                                )
                except Exception as e:
                    continue

    print(f"   Found {len(issues['unsafe_value'])} potentially unsafe .value calls")

    # Pattern 3: Unsafe datetime.fromisoformat() calls
    print("\n3️⃣ Analyzing unsafe datetime.fromisoformat() calls...")
    fromisoformat_pattern = r"datetime\.fromisoformat\("

    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                        lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        if re.search(fromisoformat_pattern, line):
                            context = "\n".join(lines[max(0, i - 3) : i + 2])
                            if "if " not in context or "and " not in context:
                                issues["unsafe_fromisoformat"].append(
                                    {
                                        "file": filepath,
                                        "line": i,
                                        "code": line.strip(),
                                        "context": context,
                                    }
                                )
                except Exception as e:
                    continue

    print(
        f"   Found {len(issues['unsafe_fromisoformat'])} potentially unsafe fromisoformat() calls"
    )

    # Pattern 4: Missing error handling in update methods
    print("\n4️⃣ Analyzing missing error handling...")

    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()

                    # Look for update methods without try/catch
                    if "def update_" in content:
                        methods = re.findall(
                            r"def (update_\w+).*?(?=def|\Z)", content, re.DOTALL
                        )
                        for method in methods:
                            if "try:" not in method or "except" not in method:
                                issues["missing_error_handling"].append(
                                    {
                                        "file": filepath,
                                        "method": (
                                            method.split("(")[0]
                                            if "(" in method
                                            else method
                                        ),
                                        "issue": "Missing try/except block",
                                    }
                                )
                except Exception as e:
                    continue

    print(
        f"   Found {len(issues['missing_error_handling'])} methods with missing error handling"
    )

    # Pattern 5: Inconsistent field naming
    print("\n5️⃣ Analyzing field naming inconsistencies...")

    field_patterns = {
        "camelCase": r"[a-z][a-zA-Z]*[A-Z][a-zA-Z]*",
        "snake_case": r"[a-z]+_[a-z_]+",
        "mixed": r"[a-zA-Z]*[A-Z][a-zA-Z]*_[a-zA-Z]*",
    }

    field_usage = defaultdict(set)

    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()

                    # Look for field assignments and accesses
                    field_matches = re.findall(
                        r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']|\.([a-zA-Z_][a-zA-Z0-9_]*)',
                        content,
                    )
                    for match in field_matches:
                        field = match[0] or match[1]
                        if field and len(field) > 2:
                            for pattern_name, pattern in field_patterns.items():
                                if re.match(pattern, field):
                                    field_usage[pattern_name].add(field)
                                    break
                except Exception as e:
                    continue

    print(f"   camelCase fields: {len(field_usage['camelCase'])}")
    print(f"   snake_case fields: {len(field_usage['snake_case'])}")
    print(f"   mixed fields: {len(field_usage['mixed'])}")

    # Summary and recommendations
    print(f"\n📊 SYSTEMIC ISSUES SUMMARY")
    print("=" * 40)

    total_issues = sum(len(issue_list) for issue_list in issues.values())
    print(f"🚨 Total potential issues found: {total_issues}")

    if total_issues > 20:
        print(f"\n💡 RECOMMENDATION: SYSTEMATIC REFACTORING NEEDED")
        print(f"   The codebase has {total_issues} potential issues.")
        print(f"   This suggests systemic problems that require:")
        print(f"   1. Defensive programming patterns")
        print(f"   2. Type safety improvements")
        print(f"   3. Consistent error handling")
        print(f"   4. Field naming standardization")
        print(f"   5. Comprehensive testing")

        return True, issues
    else:
        print(f"\n✅ Issues are manageable with targeted fixes")
        return False, issues


def generate_fix_recommendations(needs_systematic, issues):
    """Generate specific fix recommendations"""

    print(f"\n🔧 FIX RECOMMENDATIONS")
    print("=" * 30)

    if needs_systematic:
        print(f"\n🏗️ SYSTEMATIC APPROACH RECOMMENDED:")
        print(f"   Instead of fixing issues one by one, implement:")

        print(f"\n   1. DEFENSIVE UTILITY FUNCTIONS:")
        print(f"      - safe_isoformat(value) -> str")
        print(f"      - safe_enum_value(enum_obj) -> str")
        print(f"      - safe_datetime_parse(iso_string) -> datetime")
        print(f"      - safe_field_access(obj, field, default=None)")

        print(f"\n   2. TYPE SAFETY LAYER:")
        print(f"      - Pydantic validators for all models")
        print(f"      - Runtime type checking")
        print(f"      - Automatic type conversion")

        print(f"\n   3. STANDARDIZED ERROR HANDLING:")
        print(f"      - Decorator for database operations")
        print(f"      - Consistent error response format")
        print(f"      - Automatic retry logic")

        print(f"\n   4. FIELD MAPPING STANDARDIZATION:")
        print(f"      - Single source of truth for field names")
        print(f"      - Automatic camelCase <-> snake_case conversion")
        print(f"      - Validation of field consistency")

    else:
        print(f"\n🎯 TARGETED FIXES:")
        for issue_type, issue_list in issues.items():
            if issue_list:
                print(f"   {issue_type}: {len(issue_list)} issues")
                if len(issue_list) <= 5:
                    for issue in issue_list[:3]:
                        print(
                            f"      - {issue.get('file', 'Unknown')}: {issue.get('code', issue.get('method', 'Unknown'))}"
                        )


if __name__ == "__main__":
    needs_systematic, issues = analyze_systemic_issues()
    generate_fix_recommendations(needs_systematic, issues)

    if needs_systematic:
        print(f"\n🚨 CONCLUSION: Systematic refactoring recommended")
        print(f"   The codebase would benefit from a comprehensive")
        print(f"   defensive programming and type safety overhaul.")
        sys.exit(1)
    else:
        print(f"\n✅ CONCLUSION: Targeted fixes sufficient")
        sys.exit(0)
