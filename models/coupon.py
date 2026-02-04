from sqlalchemy import Column, String, Integer, Boolean, DateTime
from datetime import datetime, timezone
import uuid

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class Coupon(Base):
    __tablename__ = "coupons"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    code = Column(String(100), unique=True, nullable=False, index=True)
    relics = Column(Integer, default=0)
    gems = Column(Integer, default=0)
    unlockAdFree = Column(Boolean, default=False)
    maxRedemptions = Column(Integer, default=1)  # -1 for unlimited
    currentRedemptions = Column(Integer, default=0)
    isActive = Column(Boolean, default=True)
    redeemedBy = Column(String(1000), default="")  # Comma-separated list of player names
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "objectId": self.objectId,
            "code": self.code,
            "relics": self.relics or 0,
            "gems": self.gems or 0,
            "unlockAdFree": self.unlockAdFree or False,
            "maxRedemptions": self.maxRedemptions,
            "currentRedemptions": self.currentRedemptions or 0,
            "isActive": self.isActive,
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
