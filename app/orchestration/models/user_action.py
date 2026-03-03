import uuid
from sqlalchemy import Column, Text, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class UserAction(Base):
    __tablename__ = "oc_user_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    idempotency_key = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="RECEIVED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("workflow_id", "idempotency_key", name="uq_oc_user_actions_idempotency"),)
