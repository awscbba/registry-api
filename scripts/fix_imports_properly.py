#!/usr/bin/env python3
"""
Properly fix all import issues based on actual model classes.
"""

import os
import re


def fix_all_imports():
    """Fix all import issues properly."""

    # Correct imports based on actual model classes
    correct_imports = {
        "subscription": "from src.models.subscription import SubscriptionBase, SubscriptionCreate, SubscriptionUpdate, SubscriptionStatus",
        "project": "from src.models.project import ProjectBase, ProjectCreate, ProjectUpdate, ProjectStatus",
        "person": "from src.models.person import Person, PersonCreate, PersonUpdate, Address",
    }

    # Files that need fixing
    test_files = [
        "tests/test_subscription_email.py",
        "tests/test_all_update_inconsistencies.py",
        "tests/test_enum_fixes.py",
        "tests/test_enum_handling_issue.py",
        "tests/test_defensive_approach.py",
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"Fixing {file_path}...")
            fix_single_file(file_path, correct_imports)


def fix_single_file(file_path, correct_imports):
    """Fix imports in a single file."""

    with open(file_path, "r") as f:
        content = f.read()

    # Fix subscription imports
    content = re.sub(
        r"from src\.models\.subscription import.*",
        correct_imports["subscription"],
        content,
    )

    # Fix project imports
    content = re.sub(
        r"from src\.models\.project import.*", correct_imports["project"], content
    )

    # Fix person imports
    content = re.sub(
        r"from src\.models\.person import.*", correct_imports["person"], content
    )

    # Replace usage of non-existent classes
    content = content.replace("Subscription(", "SubscriptionBase(")
    content = content.replace("Project(", "ProjectBase(")

    with open(file_path, "w") as f:
        f.write(content)

    print(f"  ✅ Fixed {file_path}")


if __name__ == "__main__":
    print("🔧 Properly Fixing All Imports")
    print("=" * 50)

    fix_all_imports()

    print("\n✅ All imports fixed properly!")
