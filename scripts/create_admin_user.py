#!/usr/bin/env python3
"""
Script to create an admin user in the database
Usage: python scripts/create_admin_user.py <email> <password> <first_name> <last_name>
"""
import sys
import asyncio
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.repositories.people_repository import PeopleRepository
from src.models.person import PersonCreate
from src.utils.password_utils import PasswordHasher, PasswordValidator


async def create_admin_user(email: str, password: str, first_name: str, last_name: str):
    """Create an admin user in the database"""
    try:
        repo = PeopleRepository()

        print(f"Creating admin user: {email}")

        # Check if user already exists
        existing_people = await repo.list_all()
        for person in existing_people:
            existing_email = getattr(person, "email", None) or (
                person.get("email") if isinstance(person, dict) else None
            )
            if existing_email == email:
                print(f"❌ User with email {email} already exists!")
                return False

        # Validate password
        is_valid, errors = PasswordValidator.validate_password(password)
        if not is_valid:
            print(f"❌ Password validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False

        # Hash password using bcrypt
        password_hash = PasswordHasher.hash_password(password)

        # Create user data
        user_data = PersonCreate(
            firstName=first_name,
            lastName=last_name,
            email=email,
            passwordHash=password_hash,  # Use proper bcrypt hash
            phone="",  # Optional
            dateOfBirth="1990-01-01",  # Default date
            address={
                "street": "",
                "city": "",
                "state": "",
                "country": "",
                "postalCode": "",
            },
            isActive=True,
            isAdmin=True,  # Set admin flag
        )

        # Create the user
        created_user = await repo.create(user_data)

        print(f"✅ Admin user created successfully!")
        print(f"  ID: {getattr(created_user, 'id', 'N/A')}")
        print(f"  Email: {email}")
        print(f"  Name: {first_name} {last_name}")
        print(f"  Password: [HASHED]")

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python scripts/create_admin_user.py <email> <password> <first_name> <last_name>"
        )
        print(
            "Example: python scripts/create_admin_user.py admin@example.com mypassword Admin User"
        )
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    first_name = sys.argv[3]
    last_name = sys.argv[4]

    success = asyncio.run(create_admin_user(email, password, first_name, last_name))
    sys.exit(0 if success else 1)
