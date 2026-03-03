import asyncio
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.orchestration.repository import (
    WorkflowRepository,
    StageRunRepository,
    ArtifactRepository,
    EventLogRepository,
    UserActionRepository,
)
from app.orchestration.events import (
    write_event,
    append_event,
    EV_WORKFLOW_CREATED,
    EV_STAGE_SCHEDULED,
    EV_USER_ACTION_APPLIED,
)
from app.orchestration.events.schema import EV_ARTIFACT_CREATED
from app.orchestration.fsm import WorkflowStatus, get_initial_stage, get_next_stage_after, GRAPH_RUN
from app.orchestration.dispatcher.runner import run_stage, schedule_next_stage

router = APIRouter()


class CreateWorkflowRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    input_params: dict | None = None
    minimal: bool = False


class CreateWorkflowChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    input_params: dict | None = None


class UserActionRequest(BaseModel):
    type: str
    payload: dict | None = None
    idempotency_key: str


class RerunRequest(BaseModel):
    stage: str
    scope_key: str | None = None


@router.post("/workflows", response_model=dict)
def create_workflow(body: CreateWorkflowRequest = Body(default=CreateWorkflowRequest()), db: Session = Depends(get_db)):
    w_repo = WorkflowRepository(db)
    sr_repo = StageRunRepository(db)
    initial = get_initial_stage()
    w = w_repo.create(
        conversation_id=body.conversation_id,
        input_params=body.input_params or {},
        initial_stage=initial,
    )
    sr = sr_repo.create(workflow_id=w.id, stage=initial, attempt=1)
    write_event(db, w.id, EV_WORKFLOW_CREATED, {"workflow_id": str(w.id)}, w.conversation_id)
    write_event(db, w.id, EV_STAGE_SCHEDULED, {"stage_run_id": str(sr.id), "stage": initial}, w.conversation_id)
    db.commit()
    return {"workflow_id": str(w.id), "stage_run_id": str(sr.id)}


@router.post("/workflows/chat", response_model=dict)
def create_workflow_chat(
    request: Request,
    db: Session = Depends(get_db),
    body: CreateWorkflowChatRequest = Body(default=CreateWorkflowChatRequest()),
):
    w_repo = WorkflowRepository(db)
    w = w_repo.create(
        conversation_id=body.conversation_id,
        input_params=body.input_params or {},
        initial_stage=None,
    )
    envelope = append_event(db, w.id, EV_WORKFLOW_CREATED, {}, w.conversation_id)
    db.commit()
    _broadcast_envelope(request, w.id, envelope)
    return {"workflow_id": str(w.id)}


@router.post("/workflows/{workflow_id}/process", response_model=dict)
def process_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    w_repo = WorkflowRepository(db)
    sr_repo = StageRunRepository(db)
    w = w_repo.get(workflow_id)
    if not w:
        raise HTTPException(status_code=404, detail="workflow not found")
    pending = sr_repo.get_pending_for_workflow(workflow_id)
    processed = 0
    for sr in pending:
        run_stage(db, sr.id)
        processed += 1
    db.commit()
    w2 = w_repo.get(workflow_id)
    return {"processed": processed, "status": w2.status if w2 else None}


def _broadcast_envelope(request: Request, workflow_id: uuid.UUID, envelope: dict) -> None:
    broadcaster = getattr(request.app.state, "ws_broadcaster", None)
    if broadcaster:
        loop = getattr(request.app.state, "_loop", None)
        if loop:
            asyncio.run_coroutine_threadsafe(
                broadcaster.broadcast(str(workflow_id), envelope), loop
            )


@router.post("/workflows/{workflow_id}/user-actions", response_model=dict)
def submit_user_action(
    workflow_id: uuid.UUID,
    body: UserActionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    w_repo = WorkflowRepository(db)
    sr_repo = StageRunRepository(db)
    ua_repo = UserActionRepository(db)
    existing = ua_repo.get_by_idempotency(workflow_id, body.idempotency_key)
    if existing:
        db.commit()
        return {"action_id": str(existing.id), "status": existing.status}
    w = w_repo.get(workflow_id)
    if not w:
        raise HTTPException(status_code=404, detail="workflow not found")
    if body.type == "rerun_section":
        if w.status not in (WorkflowStatus.WAITING_USER, WorkflowStatus.COMPLETED):
            raise HTTPException(status_code=400, detail="workflow must be WAITING_USER or COMPLETED for rerun_section")
    elif w.status != WorkflowStatus.WAITING_USER:
        raise HTTPException(status_code=400, detail="workflow not waiting for user action")
    ua = ua_repo.create(
        workflow_id=workflow_id,
        action_type=body.type,
        payload=body.payload,
        idempotency_key=body.idempotency_key,
    )
    if body.type == "rerun_section":
        section_id = (body.payload or {}).get("section_id")
        if not section_id:
            raise HTTPException(status_code=400, detail="rerun_section requires payload.section_id")
        outline = (w.input_params or {}).get("outline", {})
        w_repo.update_status(workflow_id, WorkflowStatus.RUNNING, current_stage=GRAPH_RUN)
        attempt = sr_repo.max_attempt(workflow_id, GRAPH_RUN, scope_key=section_id) + 1
        sr = sr_repo.create(workflow_id=workflow_id, stage=GRAPH_RUN, attempt=attempt, scope_key=section_id)
        write_event(db, workflow_id, EV_STAGE_SCHEDULED, {"stage_run_id": str(sr.id), "stage": GRAPH_RUN, "scope_key": section_id, "attempt": attempt}, w.conversation_id)
        db.flush()
        run_stage(db, sr.id)
    elif body.type == "confirm_outline":
        a_repo = ArtifactRepository(db)
        outline = (body.payload or {}).get("outline", {})
        art = a_repo.create(
            workflow_id=workflow_id,
            artifact_type="outline_plan",
            stage_run_id=None,
            content_json=outline,
            title="Outline Plan (user confirmed)",
            content_preview=str(outline)[:200] if outline else "",
            created_by="user",
        )
        write_event(db, workflow_id, EV_ARTIFACT_CREATED, {"artifact_id": str(art.id), "type": art.type, "version": art.version}, w.conversation_id)
        w_repo.update_input_params(workflow_id, {"outline_confirmed": True, "outline": outline})
        w_repo.update_status(workflow_id, WorkflowStatus.RUNNING, current_stage=GRAPH_RUN)
        attempt = sr_repo.max_attempt(workflow_id, GRAPH_RUN) + 1
        sr = sr_repo.create(workflow_id=workflow_id, stage=GRAPH_RUN, attempt=attempt)
        write_event(db, workflow_id, EV_STAGE_SCHEDULED, {"stage_run_id": str(sr.id), "stage": GRAPH_RUN, "attempt": attempt}, w.conversation_id)
        db.flush()
        run_stage(db, sr.id)
    else:
        next_stage = get_next_stage_after("WAIT_OUTLINE_CONFIRM")
        if next_stage:
            w_repo.update_status(workflow_id, WorkflowStatus.RUNNING, current_stage=next_stage)
            schedule_next_stage(db, workflow_id, next_stage, w.conversation_id)
    ua_repo.set_applied(ua.id)
    envelope = append_event(
        db, workflow_id, EV_USER_ACTION_APPLIED,
        {"action_id": str(ua.id), "type": body.type},
        w.conversation_id,
    )
    db.commit()
    _broadcast_envelope(request, workflow_id, envelope)
    return {"action_id": str(ua.id), "status": "APPLIED"}


def _event_envelope(workflow_id: uuid.UUID, e) -> dict:
    return {
        "workflow_id": str(workflow_id),
        "seq": e.seq,
        "type": e.type,
        "payload": e.payload or {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/workflows/{workflow_id}/events", response_model=dict)
def list_events(
    workflow_id: uuid.UUID,
    after_seq: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    if after_seq < 0:
        raise HTTPException(status_code=400, detail="after_seq must be >= 0")
    limit = min(max(1, limit), 200)
    w_repo = WorkflowRepository(db)
    e_repo = EventLogRepository(db)
    if not w_repo.get(workflow_id):
        raise HTTPException(status_code=404, detail="workflow not found")
    events = e_repo.list_after(workflow_id, after_seq=after_seq, limit=limit)
    last_seq = max(e.seq for e in events) if events else e_repo.max_seq(workflow_id)
    return {
        "events": [_event_envelope(workflow_id, e) for e in events],
        "last_seq": last_seq,
    }


@router.get("/workflows/{workflow_id}/artifacts", response_model=dict)
def list_artifacts(
    workflow_id: uuid.UUID,
    type: str | None = None,
    scope: str | None = None,
    db: Session = Depends(get_db),
):
    w_repo = WorkflowRepository(db)
    a_repo = ArtifactRepository(db)
    if not w_repo.get(workflow_id):
        raise HTTPException(status_code=404, detail="workflow not found")
    arts = a_repo.list_by_workflow(workflow_id, artifact_type=type, scope_key=scope)
    return {
        "workflow_id": str(workflow_id),
        "artifacts": [
            {
                "id": str(a.id),
                "type": a.type,
                "version": a.version,
                "scope_key": a.scope_key,
                "title": a.title,
                "content_preview": a.content_preview,
                "content_json": a.content_json,
                "created_by": a.created_by,
            }
            for a in arts
        ],
    }


@router.get("/workflows/{workflow_id}", response_model=dict)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)):
    w_repo = WorkflowRepository(db)
    w = w_repo.get(workflow_id)
    if not w:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {
        "workflow_id": str(w.id),
        "status": w.status,
        "current_stage": w.current_stage,
        "input_params": w.input_params,
        "error_message": w.error_message,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.post("/workflows/{workflow_id}/rerun", response_model=dict)
def rerun_stage(
    workflow_id: uuid.UUID,
    body: RerunRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    w_repo = WorkflowRepository(db)
    sr_repo = StageRunRepository(db)
    w = w_repo.get(workflow_id)
    if not w:
        raise HTTPException(status_code=404, detail="workflow not found")
    attempt = sr_repo.max_attempt(workflow_id, body.stage, body.scope_key) + 1
    sr = sr_repo.create(
        workflow_id=workflow_id,
        stage=body.stage,
        attempt=attempt,
        scope_key=body.scope_key,
    )
    envelope = append_event(
        db, workflow_id, EV_STAGE_SCHEDULED,
        {"stage_run_id": str(sr.id), "stage": body.stage, "attempt": attempt},
        w.conversation_id,
    )
    db.commit()
    _broadcast_envelope(request, workflow_id, envelope)
    run_stage(db, sr.id)
    db.commit()
    return {"stage_run_id": str(sr.id), "stage": body.stage, "attempt": attempt}
