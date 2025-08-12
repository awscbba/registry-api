#!/usr/bin/env python3
"""
Generate the correct password hash for the admin user.
"""

import bcrypt
import json


def generate_password_hash():
    """Generate password hash for awsugcbba2025."""

    password = "awsugcbba2025"

    # Use the same method as the deployed code (12 rounds)
    SALT_ROUNDS = 12
    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    password_hash = hashed.decode("utf-8")

    print(f"Password: {password}")
    print(f"Hash: {password_hash}")

    # Verify the hash works
    if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        print("✅ Hash verification successful!")
    else:
        print("❌ Hash verification failed!")

    # Test against the current hash in the database
    current_hash = "$2b$12$S4fPR3/w0Fm7LChoiyPbne4HIGFgJPibJUZRm1xoMMYY0BeWgh1Su"
    print(f"\nTesting current hash: {current_hash}")

    if bcrypt.checkpw(password.encode("utf-8"), current_hash.encode("utf-8")):
        print("✅ Current hash matches the password!")
    else:
        print("❌ Current hash does NOT match the password!")
        print("This explains why login is failing.")

    return password_hash


if __name__ == "__main__":
    generate_password_hash()
