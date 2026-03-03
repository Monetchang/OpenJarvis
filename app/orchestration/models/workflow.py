import uuid
from sqlalchemy import Column, Text, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Workflow(Base):
    __tablename__ = "oc_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Text, nullable=False, default="CREATED")
    current_stage = Column(Text, nullable=True)
    input_params = Column(JSONB, nullable=True)
    active_reference_set_version = Column(Integer, nullable=True)
    active_outline_version = Column(Integer, nullable=True)
    active_draft_version = Column(Integer, nullable=True)
    active_artifacts = Column(JSONB, nullable=True)
    error_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    lock_version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_oc_workflows_conversation_created", "conversation_id", "created_at"),)
