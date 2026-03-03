import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.orchestration.models import UserAction


class UserActionRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_by_idempotency(self, workflow_id: uuid.UUID, idempotency_key: str) -> UserAction | None:
        return (
            self._db.query(UserAction)
            .filter(
                UserAction.workflow_id == workflow_id,
                UserAction.idempotency_key == idempotency_key,
            )
            .first()
        )

    def create(
        self,
        workflow_id: uuid.UUID,
        action_type: str,
        payload: dict | None = None,
        idempotency_key: str = "",
    ) -> UserAction:
        ua = UserAction(
            workflow_id=workflow_id,
            type=action_type,
            payload=payload or {},
            idempotency_key=idempotency_key,
            status="RECEIVED",
        )
        self._db.add(ua)
        self._db.flush()
        return ua

    def set_applied(self, action_id: uuid.UUID) -> None:
        ua = self._db.query(UserAction).filter(UserAction.id == action_id).first()
        if ua:
            ua.status = "APPLIED"
            ua.applied_at = datetime.utcnow()

    def set_rejected(self, action_id: uuid.UUID) -> None:
        ua = self._db.query(UserAction).filter(UserAction.id == action_id).first()
        if ua:
            ua.status = "REJECTED"
