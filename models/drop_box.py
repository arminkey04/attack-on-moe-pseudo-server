from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import json

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class DropBox(Base):
    """Mail/Inbox item for sending rewards to users

    Supported types (from DropBoxItemType enum):
    - "Gold": In-game gold currency (金币)
    - "Gems": Premium currency (宝石)
    - "MoeCrystal": Special currency (萌水晶)
    - "Ruby": Moe soul currency (萌魂) - custom addition
    - "Moetifacts": Artifact items
    - "MoetanPackages": Character packages
    - "AdFree": Ad-free privilege
    """
    __tablename__ = "drop_boxes"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    userId = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=True)
    title = Column(Text, nullable=True)  # JSON string: {"en": "...", "zh": "..."}
    value = Column(String(255), nullable=True)
    msg = Column(String(500), nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", backref="drop_boxes")

    def to_dict(self):
        title_dict = {}
        if self.title:
            try:
                title_dict = json.loads(self.title)
            except:
                title_dict = {"en": self.title}

        result = {
            "objectId": self.objectId,
            "type": self.type or "",
            "title": title_dict,
            "value": self.value or "",
            "msg": self.msg or "",
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }

        # Add user pointer for Parse SDK compatibility
        if self.userId:
            result["user"] = {
                "__type": "Pointer",
                "className": "_User",
                "objectId": self.userId
            }

        return result
