import uuid
from sqlalchemy import Column, Text, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class Artifact(Base):
    __tablename__ = "oc_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    stage_run_id = Column(UUID(as_uuid=True), nullable=True)
    type = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    scope_key = Column(Text, nullable=True, default="global")
    title = Column(Text, nullable=True)
    content_uri = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    content_json = Column(JSONB, nullable=True)
    created_by = Column(Text, nullable=False, default="agent")
    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_oc_artifacts_workflow_type_version", "workflow_id", "type", "version"),
    )
