import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.orchestration.models import StageRun


class StageRunRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(
        self,
        workflow_id: uuid.UUID,
        stage: str,
        attempt: int = 1,
        scope_key: str | None = None,
        parent_stage_run_id: uuid.UUID | None = None,
        input_snapshot: dict | None = None,
    ) -> StageRun:
        sr = StageRun(
            workflow_id=workflow_id,
            stage=stage,
            status="CREATED",
            attempt=attempt,
            scope_key=scope_key,
            parent_stage_run_id=parent_stage_run_id,
            input_snapshot=input_snapshot or {},
        )
        self._db.add(sr)
        self._db.flush()
        return sr

    def get(self, stage_run_id: uuid.UUID) -> StageRun | None:
        return self._db.query(StageRun).filter(StageRun.id == stage_run_id).first()

    def get_for_update(self, stage_run_id: uuid.UUID) -> StageRun | None:
        return (
            self._db.query(StageRun)
            .filter(StageRun.id == stage_run_id)
            .with_for_update()
            .first()
        )

    def get_pending_for_workflow(self, workflow_id: uuid.UUID) -> list[StageRun]:
        return (
            self._db.query(StageRun)
            .filter(
                and_(
                    StageRun.workflow_id == workflow_id,
                    StageRun.status == "CREATED",
                )
            )
            .order_by(StageRun.created_at)
            .all()
        )

    def has_running(self, workflow_id: uuid.UUID) -> bool:
        return (
            self._db.query(StageRun)
            .filter(
                and_(
                    StageRun.workflow_id == workflow_id,
                    StageRun.status == "RUNNING",
                )
            )
            .first()
            is not None
        )

    def get_running_run(self, workflow_id: uuid.UUID) -> StageRun | None:
        """Return the RUNNING stage_run for workflow_id, or None."""
        return (
            self._db.query(StageRun)
            .filter(
                StageRun.workflow_id == workflow_id,
                StageRun.status == "RUNNING",
            )
            .first()
        )

    def max_attempt(self, workflow_id: uuid.UUID, stage: str, scope_key: str | None = None) -> int:
        q = self._db.query(StageRun).filter(
            and_(
                StageRun.workflow_id == workflow_id,
                StageRun.stage == stage,
            )
        )
        if scope_key is not None:
            q = q.filter(StageRun.scope_key == scope_key)
        r = q.order_by(StageRun.attempt.desc()).first()
        return r.attempt if r else 0

    def set_running(self, stage_run_id: uuid.UUID) -> None:
        sr = self.get(stage_run_id)
        if sr:
            sr.status = "RUNNING"
            sr.started_at = datetime.utcnow()

    def set_succeeded(
        self,
        stage_run_id: uuid.UUID,
        output_artifact_ids: list[uuid.UUID] | None = None,
        cost_meta: dict | None = None,
    ) -> None:
        sr = self.get(stage_run_id)
        if sr:
            sr.status = "SUCCEEDED"
            sr.finished_at = datetime.utcnow()
            if output_artifact_ids is not None:
                sr.output_artifact_ids = output_artifact_ids
            if cost_meta is not None:
                sr.cost_meta = cost_meta

    def set_failed(self, stage_run_id: uuid.UUID, error_message: str) -> None:
        sr = self.get(stage_run_id)
        if sr:
            sr.status = "FAILED"
            sr.finished_at = datetime.utcnow()
            sr.error_message = error_message
