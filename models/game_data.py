from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class GameData(Base):
    __tablename__ = "game_data"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    userId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False, index=True)
    data = Column(Text, nullable=True)  # JSON string of SaveData
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="game_data")

    def to_dict(self):
        return {
            "objectId": self.objectId,
            "user": {
                "__type": "Pointer",
                "className": "_User",
                "objectId": self.userId
            },
            "data": self.data,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
