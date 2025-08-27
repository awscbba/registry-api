"""
Authentication service implementation.
Handles business logic for authentication operations.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..core.config import config
from ..repositories.people_repository import PeopleRepository
from ..models.auth import LoginResponse, User
from ..models.person import PersonResponse


class AuthService:
    """Service for authentication business logic."""

    def __init__(self):
        self.people_repository = PeopleRepository()
        self.jwt_secret = config.auth.jwt_secret
        self.jwt_algorithm = config.auth.jwt_algorithm
        self.access_token_expire_hours = config.auth.access_token_expire_hours

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    def _generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT access token."""
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "isAdmin": user_data.get("isAdmin", False),
            "exp": datetime.utcnow() + timedelta(hours=self.access_token_expire_hours),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT refresh token."""
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "exp": datetime.utcnow()
            + timedelta(days=config.auth.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[LoginResponse]:
        """Authenticate a user with email and password."""
        # Get user by email
        person = await self.people_repository.get_by_email(email)
        if not person:
            return None

        # Check if user is active
        if not person.isActive:
            return None

        # Verify password (for now, we'll assume password is stored as plain text)
        # In production, this should be properly hashed
        if not hasattr(person, "password") or not person.password:
            return None

        # For now, simple password comparison (should be hashed in production)
        if person.password != password:
            return None

        # Generate tokens
        user_data = person.model_dump()
        access_token = self._generate_access_token(user_data)
        refresh_token = self._generate_refresh_token(user_data)

        # Create user response
        user_response = {
            "id": person.id,
            "email": person.email,
            "firstName": person.firstName,
            "lastName": person.lastName,
            "isAdmin": person.isAdmin,
            "isActive": person.isActive,
        }

        return LoginResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            user=user_response,
            expiresIn=self.access_token_expire_hours * 3600,
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        person = await self.people_repository.get_by_id(user_id)
        if not person:
            return None

        return User(
            id=person.id,
            email=person.email,
            firstName=person.firstName,
            lastName=person.lastName,
            isAdmin=person.isAdmin,
            isActive=person.isActive,
        )

    async def refresh_access_token(self, refresh_token: str) -> Optional[LoginResponse]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        person = await self.people_repository.get_by_id(user_id)
        if not person or not person.isActive:
            return None

        # Generate new tokens
        user_data = person.model_dump()
        access_token = self._generate_access_token(user_data)
        new_refresh_token = self._generate_refresh_token(user_data)

        user_response = {
            "id": person.id,
            "email": person.email,
            "firstName": person.firstName,
            "lastName": person.lastName,
            "isAdmin": person.isAdmin,
            "isActive": person.isActive,
        }

        return LoginResponse(
            accessToken=access_token,
            refreshToken=new_refresh_token,
            user=user_response,
            expiresIn=self.access_token_expire_hours * 3600,
        )
