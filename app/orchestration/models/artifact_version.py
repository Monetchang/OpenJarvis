from sqlalchemy import Column, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ArtifactVersion(Base):
    __tablename__ = "oc_artifact_versions"

    workflow_id = Column(UUID(as_uuid=True), primary_key=True)
    artifact_type = Column(Text, primary_key=True)
    scope_key = Column(Text, primary_key=True, default="global")
    current_version = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
