import uuid
from sqlalchemy.orm import Session
from app.orchestration.repository import StageRunRepository


class ConcurrencyError(Exception):
    """Another stage_run is already RUNNING for this workflow."""


def ensure_no_running_stage(db: Session, workflow_id: uuid.UUID) -> None:
    repo = StageRunRepository(db)
    if repo.has_running(workflow_id):
        raise ConcurrencyError("workflow already has a RUNNING stage_run")
