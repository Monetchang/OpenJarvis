import uuid
from sqlalchemy import Column, Text, BigInteger, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class EventLog(Base):
    __tablename__ = "oc_event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=True)
    type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    seq = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("uq_oc_event_logs_workflow_seq", "workflow_id", "seq", unique=True),)
