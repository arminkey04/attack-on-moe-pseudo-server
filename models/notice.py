from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime, timezone
import uuid
import json

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


class Notice(Base):
    __tablename__ = "notices"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    imageURL = Column(String(500), nullable=True)
    order = Column(Integer, default=0)
    text = Column(Text, nullable=True)  # JSON string: {"en": "...", "zh": "..."}
    url = Column(String(500), nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        text_dict = {}
        if self.text:
            try:
                text_dict = json.loads(self.text)
            except:
                text_dict = {"en": self.text}

        return {
            "objectId": self.objectId,
            "imageURL": self.imageURL or "",
            "order": self.order or 0,
            "text": text_dict,
            "url": self.url or "",
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
