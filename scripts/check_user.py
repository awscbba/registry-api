#!/usr/bin/env python3
"""
Script to check if a user exists in the database
Usage: python scripts/check_user.py <email>
"""
import sys
import asyncio
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.repositories.people_repository import PeopleRepository


async def check_user(email: str):
    """Check if a user exists in the database"""
    try:
        repo = PeopleRepository()
        people = await repo.list_all()

        print(f"Checking for user: {email}")
        print(f"Total people in database: {len(people)}")

        for person in people:
            # Handle both Pydantic models and dictionaries
            if hasattr(person, "email"):
                person_email = getattr(person, "email", "No email")
                first_name = getattr(person, "firstName", "")
                last_name = getattr(person, "lastName", "")
                is_active = getattr(person, "isActive", "Unknown")
                is_admin = getattr(person, "isAdmin", False)
                has_password = bool(getattr(person, "passwordHash", None))
                person_id = getattr(person, "id", "No ID")
            else:
                person_email = (
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
                has_password = (
                    bool(person.get("passwordHash", None))
                    if isinstance(person, dict)
                    else False
                )
                person_id = (
                    person.get("id", "No ID") if isinstance(person, dict) else "No ID"
                )

            if person_email == email:

                print(f"✅ User found:")
                print(f"  ID: {person_id}")
                print(f"  Email: {person_email}")
                print(f"  First Name: {first_name}")
                print(f"  Last Name: {last_name}")
                print(f"  Is Active: {is_active}")
                print(f"  Is Admin: {is_admin}")
                print(f"  Has Password: {has_password}")
                return True

        print(f"❌ User not found: {email}")
        return False

    except Exception as e:
        print(f"❌ Error checking user: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_user.py <email>")
        print("Example: python scripts/check_user.py admin@example.com")
        sys.exit(1)

    email = sys.argv[1]
    found = asyncio.run(check_user(email))
    sys.exit(0 if found else 1)
