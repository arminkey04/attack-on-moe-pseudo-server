from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

import sys
sys.path.append('..')
from database import Base
from models.user import format_parse_date


def generate_object_id():
    return uuid.uuid4().hex[:10]


# Association table for many-to-many relationship
friend_relation_users = Table(
    'friend_relation_users',
    Base.metadata,
    Column('friend_relation_id', String(10), ForeignKey('friend_relations.objectId', ondelete="CASCADE")),
    Column('user_id', String(10), ForeignKey('users.objectId', ondelete="CASCADE"))
)


class FriendRelation(Base):
    __tablename__ = "friend_relations"

    objectId = Column(String(10), primary_key=True, default=generate_object_id)
    user1Id = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False)
    user2Id = Column(String(10), ForeignKey("users.objectId", ondelete="CASCADE"), nullable=False)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updatedAt = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "objectId": self.objectId,
            "users": [
                {"__type": "Pointer", "className": "_User", "objectId": self.user1Id},
                {"__type": "Pointer", "className": "_User", "objectId": self.user2Id}
            ],
            "createdAt": format_parse_date(self.createdAt),
            "updatedAt": format_parse_date(self.updatedAt),
        }
