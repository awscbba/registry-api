#!/usr/bin/env python3
"""
Script to list all users in the database
Usage: python scripts/list_users.py
"""
import sys
import asyncio
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.repositories.people_repository import PeopleRepository


async def list_all_users():
    """List all users in the database"""
    try:
        repo = PeopleRepository()
        people = await repo.list_all()

        print(f"Total users: {len(people)}")

        if not people:
            print("No users found in the database.")
            return True

        for i, person in enumerate(people, 1):
            # Handle both object attributes and dictionary access
            if hasattr(person, "email"):
                email = getattr(person, "email", "No email")
                first_name = getattr(person, "firstName", "")
                last_name = getattr(person, "lastName", "")
                is_active = getattr(person, "isActive", "Unknown")
                is_admin = getattr(person, "isAdmin", False)
            else:
                email = (
                    person.get("email", "No email")
                    if isinstance(person, dict)
                    else "No email"
                )
                first_name = (
                    person.get("firstName", "") if isinstance(person, dict) else ""
                )
                last_name = (
                    person.get("lastName", "") if isinstance(person, dict) else ""
                )
                is_active = (
                    person.get("isActive", "Unknown")
                    if isinstance(person, dict)
                    else "Unknown"
                )
                is_admin = (
                    person.get("isAdmin", False) if isinstance(person, dict) else False
                )

            name = f"{first_name} {last_name}".strip()
            status = "✅ Active" if is_active else "❌ Inactive"
            admin_badge = " 👑 Admin" if is_admin else ""

            print(f"{i}. {email} ({name}) - {status}{admin_badge}")

        return True

    except Exception as e:
        print(f"❌ Error listing users: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(list_all_users())
    sys.exit(0 if success else 1)
