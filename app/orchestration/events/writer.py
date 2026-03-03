import uuid
from sqlalchemy.orm import Session
from app.orchestration.repository import EventLogRepository


def event_to_envelope(e) -> dict:
    return {
        "workflow_id": str(e.workflow_id),
        "seq": e.seq,
        "type": e.type,
        "payload": e.payload or {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def append_event(
    db: Session,
    workflow_id: uuid.UUID,
    event_type: str,
    payload: dict | None = None,
    conversation_id: uuid.UUID | None = None,
) -> dict:
    repo = EventLogRepository(db)
    e = repo.append(
        workflow_id=workflow_id,
        event_type=event_type,
        payload=payload,
        conversation_id=conversation_id,
    )
    return event_to_envelope(e)


def write_event(
    db: Session,
    workflow_id: uuid.UUID,
    event_type: str,
    payload: dict | None = None,
    conversation_id: uuid.UUID | None = None,
) -> None:
    append_event(db, workflow_id, event_type, payload, conversation_id)
