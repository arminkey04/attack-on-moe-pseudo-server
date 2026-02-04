from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class UserSummary(Base):
    __tablename__ = "user_summaries"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    userId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False, unique=True)
    displayName = Column(String(255), default="")
    friendPoint = Column(Integer, default=0)
    friendLimit = Column(Integer, default=5)
    ruby = Column(Integer, default=0)
    gem = Column(Integer, default=0)
    moecrystal = Column(Integer, default=0)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="user_summary")

    def to_dict(self):
        return {
            "objectId": self.objectId,
            "user": {
                "__type": "Pointer",
                "className": "_User",
                "objectId": self.userId
            },
            "displayName": self.displayName or "",
            "friendPoint": self.friendPoint or 0,
            "friendLimit": self.friendLimit or 5,
            "ruby": self.ruby or 0,
            "gem": self.gem or 0,
            "moecrystal": self.moecrystal or 0,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
