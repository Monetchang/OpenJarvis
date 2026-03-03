import uuid
from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "oc_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
