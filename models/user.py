from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import hashlib

import sys
sys.path.append('..')
from database import Base


def generate_object_id():
    return uuid.uuid4().hex[:10]


def format_parse_date(dt: datetime) -> str:
    """Format datetime to Parse SDK expected format: yyyy-MM-ddTHH:mm:ss.fffZ"""
    if dt is None:
        return None
    # Ensure we have UTC time
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Format with milliseconds
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


class User(Base):
    __tablename__ = "users"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    googleUserId = Column(String(255), nullable=True, unique=True, index=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    user_summary = relationship("UserSummary", back_populates="user", uselist=False, cascade="all, delete-orphan")
    game_data = relationship("GameData", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Hash and set the password"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verify the password against the stored hash"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self, include_session_token=False):
        result = {
            "objectId": self.objectId,
            "username": self.username,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
        if self.email:
            result["email"] = self.email
        if self.googleUserId:
            result["googleUserId"] = self.googleUserId
        return result

    def to_parse_response(self):
        """Return Parse-compatible response format

        Note: createdAt and updatedAt should be plain strings, not Date objects.
        ParseObjectCoder.Decode expects: ParseDecoder.ParseDate(obj as string)
        """
        result = {
            "objectId": self.objectId,
            "username": self.username,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
        if self.email:
            result["email"] = self.email
        if self.googleUserId:
            result["googleUserId"] = self.googleUserId
        return result


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sessionToken = Column(String(255), unique=True, nullable=False, index=True)
    userId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expiresAt = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
