#!/usr/bin/env python3
"""
Verify which table contains the user and check data consistency.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import config
from src.repositories.people_repository import PeopleRepository


def main():
    """Check user data in configured table."""
    repo = PeopleRepository()

    print(f"✓ Using table: {repo.table_name}")
    print(f"✓ Config people_table: {config.database.people_table}")
    print(f"✓ Config people_table_legacy: {config.database.people_table_legacy}")
    print()

    # Check for specific user
    email = "sergio.rodriguez@cbba.cloud.org.bo"
    user = repo.get_by_email(email)

    if user:
        print(f"✓ Found user: {user.email}")
        print(f"  - ID: {user.id}")
        print(f"  - Name: {user.firstName} {user.lastName}")
        print(f"  - Phone: {user.phone}")
        print(f"  - Date of Birth: {user.dateOfBirth}")
        print(f"  - Address: {user.address}")
        print(f"  - Is Admin: {user.isAdmin}")
    else:
        print(f"✗ User not found: {email}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
