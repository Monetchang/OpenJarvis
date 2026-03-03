import uuid
from sqlalchemy.orm import Session
from app.orchestration.models import Workflow


class WorkflowRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(
        self,
        conversation_id: uuid.UUID | None = None,
        input_params: dict | None = None,
        initial_stage: str | None = None,
    ) -> Workflow:
        w = Workflow(
            conversation_id=conversation_id,
            status="CREATED",
            current_stage=initial_stage,
            input_params=input_params or {},
        )
        self._db.add(w)
        self._db.flush()
        return w

    def get(self, workflow_id: uuid.UUID) -> Workflow | None:
        return self._db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def get_for_update(self, workflow_id: uuid.UUID) -> Workflow | None:
        return (
            self._db.query(Workflow)
            .filter(Workflow.id == workflow_id)
            .with_for_update()
            .first()
        )

    def update_status(
        self,
        workflow_id: uuid.UUID,
        status: str,
        current_stage: str | None = None,
        error_message: str | None = None,
        error_code: str | None = None,
    ) -> None:
        w = self.get(workflow_id)
        if w:
            w.status = status
            if current_stage is not None:
                w.current_stage = current_stage
            if error_message is not None:
                w.error_message = error_message
            if error_code is not None:
                w.error_code = error_code
            w.lock_version += 1

    def update_input_params(self, workflow_id: uuid.UUID, merge: dict) -> None:
        w = self.get(workflow_id)
        if w:
            params = dict(w.input_params or {})
            params.update(merge)
            w.input_params = params
