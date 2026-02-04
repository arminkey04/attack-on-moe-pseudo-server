from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import uuid
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.user import User, Session
from models.user_summary import UserSummary
from config import settings


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256 (matching User model)"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password using SHA256 (matching User model)"""
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

    @staticmethod
    def generate_session_token() -> str:
        return f"r:{secrets.token_hex(24)}"

    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        password: str,
        email: Optional[str] = None,
        google_user_id: Optional[str] = None
    ) -> tuple[User, str]:
        """Create a new user and return the user with session token"""
        # Check if username already exists
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise ValueError("Username already exists")

        # Create user
        user = User(
            username=username,
            password_hash=AuthService.hash_password(password),
            email=email,
            googleUserId=google_user_id
        )
        db.add(user)
        await db.flush()

        # Create session
        session_token = AuthService.generate_session_token()
        session = Session(
            sessionToken=session_token,
            userId=user.objectId,
            expiresAt=datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        )
        db.add(session)

        # Create user summary
        user_summary = UserSummary(
            userId=user.objectId,
            displayName="",
            friendPoint=0,
            friendLimit=5,
            ruby=0,
            gem=0,
            moecrystal=0
        )
        db.add(user_summary)

        await db.commit()
        await db.refresh(user)

        return user, session_token

    @staticmethod
    async def login(db: AsyncSession, username: str, password: str) -> tuple[User, str]:
        """Login user and return user with session token

        Supports login by username or email.
        """
        # Try to find user by username or email
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()

        if not user or not AuthService.verify_password(password, user.password_hash):
            raise ValueError("Invalid username or password")

        # Create new session
        session_token = AuthService.generate_session_token()
        session = Session(
            sessionToken=session_token,
            userId=user.objectId,
            expiresAt=datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        )
        db.add(session)
        await db.commit()

        return user, session_token

    @staticmethod
    async def get_user_by_session_token(db: AsyncSession, session_token: str) -> Optional[User]:
        """Get user by session token"""
        result = await db.execute(
            select(Session).where(Session.sessionToken == session_token)
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Check if session is expired
        if session.expiresAt:
            # Handle both offset-naive and offset-aware datetimes
            expires_at = session.expiresAt
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                await db.delete(session)
                await db.commit()
                return None

        result = await db.execute(select(User).where(User.objectId == session.userId))
        return result.scalar_one_or_none()

    @staticmethod
    async def logout(db: AsyncSession, session_token: str) -> bool:
        """Logout user by deleting session"""
        result = await db.execute(
            select(Session).where(Session.sessionToken == session_token)
        )
        session = result.scalar_one_or_none()

        if session:
            await db.delete(session)
            await db.commit()
            return True
        return False

    @staticmethod
    async def clear_user_sessions(db: AsyncSession, username: str, password: str) -> bool:
        """Clear all sessions for a user (used before login)

        If user doesn't exist, return True (no sessions to clear).
        If user exists but password is wrong, raise ValueError.
        """
        # Try to find user by username or email
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()

        # If user doesn't exist, return success (no sessions to clear)
        if not user:
            return True

        # If user exists, verify password
        if not AuthService.verify_password(password, user.password_hash):
            raise ValueError("Invalid username or password")

        await db.execute(delete(Session).where(Session.userId == user.objectId))
        await db.commit()
        return True

    @staticmethod
    async def get_user_by_google_id(db: AsyncSession, google_user_id: str) -> Optional[User]:
        """Get user by Google user ID"""
        result = await db.execute(select(User).where(User.googleUserId == google_user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def link_google_account(db: AsyncSession, user: User, google_user_id: str) -> User:
        """Link Google account to user"""
        # Check if Google ID is already linked to another user
        result = await db.execute(select(User).where(User.googleUserId == google_user_id))
        existing_user = result.scalar_one_or_none()

        if existing_user and existing_user.objectId != user.objectId:
            raise ValueError("Google account already linked to another user")

        user.googleUserId = google_user_id
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def create_session_for_user(db: AsyncSession, user: User) -> str:
        """Create a new session for user and return session token"""
        session_token = AuthService.generate_session_token()
        session = Session(
            sessionToken=session_token,
            userId=user.objectId,
            expiresAt=datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
        )
        db.add(session)
        await db.commit()
        return session_token
