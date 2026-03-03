import uuid
from sqlalchemy import Column, Text, Integer, DateTime, func, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.core.database import Base


class StageRun(Base):
    __tablename__ = "oc_stage_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    stage = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="CREATED")
    attempt = Column(Integer, nullable=False, default=1)
    scope_key = Column(Text, nullable=True)
    parent_stage_run_id = Column(UUID(as_uuid=True), nullable=True)
    input_snapshot = Column(JSONB, nullable=True)
    output_artifact_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    cost_meta = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_oc_stage_runs_workflow_stage_attempt", "workflow_id", "stage", "attempt"),
        Index(
            "uq_oc_stage_runs_one_running",
            "workflow_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )
