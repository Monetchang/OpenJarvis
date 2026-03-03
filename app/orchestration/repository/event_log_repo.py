import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.orchestration.models import EventLog


class EventLogRepository:
    def __init__(self, db: Session):
        self._db = db

    def max_seq(self, workflow_id: uuid.UUID) -> int:
        r = (
            self._db.query(func.coalesce(func.max(EventLog.seq), 0).label("m"))
            .filter(EventLog.workflow_id == workflow_id)
            .first()
        )
        return r.m or 0

    def next_seq(self, workflow_id: uuid.UUID) -> int:
        return self.max_seq(workflow_id) + 1

    def append(
        self,
        workflow_id: uuid.UUID,
        event_type: str,
        payload: dict | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> EventLog:
        seq = self.next_seq(workflow_id)
        e = EventLog(
            workflow_id=workflow_id,
            conversation_id=conversation_id,
            type=event_type,
            payload=payload or {},
            seq=seq,
        )
        self._db.add(e)
        self._db.flush()
        return e

    def list_after(
        self,
        workflow_id: uuid.UUID,
        after_seq: int = 0,
        limit: int = 200,
    ) -> list[EventLog]:
        return (
            self._db.query(EventLog)
            .filter(
                EventLog.workflow_id == workflow_id,
                EventLog.seq > after_seq,
            )
            .order_by(EventLog.seq)
            .limit(limit)
            .all()
        )
