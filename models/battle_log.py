from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
import uuid

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class BattleLog(Base):
    __tablename__ = "battle_logs"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    senderId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False, index=True)
    receiverId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False, index=True)
    senderScore = Column(Integer, default=0)
    receiverScore = Column(Integer, default=0)
    senderWin = Column(Boolean, default=False)
    senderClaim = Column(Boolean, default=False)
    receiverClaim = Column(Boolean, default=False)
    expired = Column(Boolean, default=False)
    receivedAt = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        result = {
            "objectId": self.objectId,
            "sender": {"__type": "Pointer", "className": "_User", "objectId": self.senderId},
            "receiver": {"__type": "Pointer", "className": "_User", "objectId": self.receiverId},
            "senderScore": self.senderScore or 0,
            "receiverScore": self.receiverScore or 0,
            "senderWin": self.senderWin or False,
            "senderClaim": self.senderClaim or False,
            "receiverClaim": self.receiverClaim or False,
            "expired": self.expired or False,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
        if self.receivedAt:
            result["receivedAt"] = {"__type": "Date", "iso": format_parse_date(self.receivedAt)}
        else:
            result["receivedAt"] = {"__type": "Date", "iso": "0001-01-01T00:00:00.000Z"}
        return result
