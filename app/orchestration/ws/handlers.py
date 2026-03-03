import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.ai import AIClient
from app.orchestration.repository import (
    WorkflowRepository,
    UserActionRepository,
    EventLogRepository,
    StageRunRepository,
    ArtifactRepository,
)
from app.orchestration.events import (
    append_event,
    write_event,
    event_to_envelope,
    EV_CHAT_MESSAGE,
    EV_USER_ACTION_APPLIED,
)
from app.orchestration.events.schema import EV_STAGE_SCHEDULED, EV_ARTIFACT_CREATED
from app.orchestration.fsm import WorkflowStatus, get_initial_stage, GRAPH_RUN
from app.orchestration.dispatcher.runner import run_stage
from app.orchestration.ws.schemas import (
    WorkflowStartPayload,
    ALLOWED_STYLES,
    ALLOWED_AUDIENCES,
)

logger = logging.getLogger(__name__)
_ai_client: AIClient | None = None


def _make_broadcast_fn(app: Any, workflow_id: uuid.UUID):
    """创建 broadcast_fn，用于流式事件实时推送到 WebSocket。"""
    broadcaster = getattr(app.state, "ws_broadcaster", None)
    loop = getattr(app.state, "_loop", None)
    if not broadcaster or not loop:
        return None

    def broadcast(envelope: dict) -> None:
        asyncio.run_coroutine_threadsafe(
            broadcaster.broadcast(str(workflow_id), envelope), loop
        )

    return broadcast


def write_action_ack_event(workflow_id: uuid.UUID, ack_payload: dict) -> dict:
    """Write action.ack to event_logs, return envelope with unique seq."""
    db = SessionLocal()
    try:
        w = WorkflowRepository(db).get(workflow_id)
        conversation_id = w.conversation_id if w else None
        env = append_event(db, workflow_id, "action.ack", ack_payload, conversation_id)
        db.commit()
        return env
    finally:
        db.close()


def try_accept_workflow_start(
    workflow_id: uuid.UUID,
    idempotency_key: str,
    input_: dict,
) -> tuple[str, int, uuid.UUID | None, str | None, dict | None]:
    """Returns (status, seq, action_id, reason, extra_payload). extra_payload for REJECTED already_running."""
    db = SessionLocal()
    try:
        e_repo = EventLogRepository(db)
        ua_repo = UserActionRepository(db)
        w_repo = WorkflowRepository(db)
        sr_repo = StageRunRepository(db)
        seq = e_repo.max_seq(workflow_id)
        w = w_repo.get(workflow_id)
        if not w:
            return ("REJECTED", seq, None, "workflow not found", None)
        if w.status != WorkflowStatus.CREATED:
            return ("REJECTED", seq, None, "workflow status does not allow workflow.start", None)
        running_sr = sr_repo.get_running_run(workflow_id)
        if running_sr:
            extra = {
                "running_run_id": str(running_sr.id),
                "running_since": running_sr.created_at.isoformat() if running_sr.created_at else None,
            }
            if running_sr.started_at:
                extra["last_heartbeat_at"] = running_sr.started_at.isoformat()
            logger.info(
                "decision=already_running workflow_id=%s running_run_id=%s run_status=%s",
                workflow_id,
                running_sr.id,
                running_sr.status,
            )
            return ("REJECTED", seq, None, "already_running", extra)
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        if existing:
            return ("DUPLICATE", seq, existing.id, None, None)
        ua = ua_repo.create(
            workflow_id=workflow_id,
            action_type="workflow.start",
            payload=input_,
            idempotency_key=idempotency_key,
        )
        db.commit()
        return ("ACCEPTED", seq, ua.id, None, None)
    except IntegrityError:
        db.rollback()
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        return ("DUPLICATE", seq, existing.id if existing else None, None, None)
    finally:
        db.close()


def try_accept_outline_confirm(
    workflow_id: uuid.UUID,
    idempotency_key: str,
    input_: dict,
) -> tuple[str, int, uuid.UUID | None, str | None]:
    """Returns (status, seq, action_id, reason)."""
    db = SessionLocal()
    try:
        e_repo = EventLogRepository(db)
        ua_repo = UserActionRepository(db)
        w_repo = WorkflowRepository(db)
        seq = e_repo.max_seq(workflow_id)
        w = w_repo.get(workflow_id)
        if not w:
            return ("REJECTED", seq, None, "workflow not found")
        if w.status != WorkflowStatus.WAITING_USER:
            return ("REJECTED", seq, None, "workflow must be WAITING_USER for outline.confirm")
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        if existing:
            return ("DUPLICATE", seq, existing.id, None)
        ua = ua_repo.create(
            workflow_id=workflow_id,
            action_type="confirm_outline",
            payload=input_,
            idempotency_key=idempotency_key,
        )
        db.commit()
        return ("ACCEPTED", seq, ua.id, None)
    except IntegrityError:
        db.rollback()
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        return ("DUPLICATE", seq, existing.id if existing else None, None)
    finally:
        db.close()


def try_accept_section_rerun(
    workflow_id: uuid.UUID,
    idempotency_key: str,
    input_: dict,
) -> tuple[str, int, uuid.UUID | None, str | None]:
    """Returns (status, seq, action_id, reason)."""
    db = SessionLocal()
    try:
        e_repo = EventLogRepository(db)
        ua_repo = UserActionRepository(db)
        w_repo = WorkflowRepository(db)
        seq = e_repo.max_seq(workflow_id)
        w = w_repo.get(workflow_id)
        if not w:
            return ("REJECTED", seq, None, "workflow not found")
        if w.status not in (WorkflowStatus.WAITING_USER, WorkflowStatus.COMPLETED):
            return ("REJECTED", seq, None, "workflow must be WAITING_USER or COMPLETED for section.rerun")
        section_id = (input_ or {}).get("section_id")
        if not section_id:
            return ("REJECTED", seq, None, "section_id required")
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        if existing:
            return ("DUPLICATE", seq, existing.id, None)
        ua = ua_repo.create(
            workflow_id=workflow_id,
            action_type="rerun_section",
            payload=input_,
            idempotency_key=idempotency_key,
        )
        db.commit()
        return ("ACCEPTED", seq, ua.id, None)
    except IntegrityError:
        db.rollback()
        existing = ua_repo.get_by_idempotency(workflow_id, idempotency_key)
        return ("DUPLICATE", seq, existing.id if existing else None, None)
    finally:
        db.close()


def apply_outline_confirm(workflow_id: uuid.UUID, ua_id: uuid.UUID, input_: dict, app: Any = None) -> list[dict]:
    """Run confirm_outline logic; ua already created. Returns new event envelopes."""
    db = SessionLocal()
    try:
        w_repo = WorkflowRepository(db)
        sr_repo = StageRunRepository(db)
        ua_repo = UserActionRepository(db)
        a_repo = ArtifactRepository(db)
        e_repo = EventLogRepository(db)
        w = w_repo.get(workflow_id)
        if not w:
            return []
        before_seq = e_repo.max_seq(workflow_id)
        outline = (input_ or {}).get("outline", {})
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
        ua_repo.set_applied(ua_id)
        append_event(db, workflow_id, EV_USER_ACTION_APPLIED, {"action_id": str(ua_id), "type": "confirm_outline"}, w.conversation_id)
        write_event(db, workflow_id, "graph.resumed", {"stage_run_id": str(sr.id), "resumed_from": "outline_confirm"}, w.conversation_id)
        db.flush()
        broadcast_fn = _make_broadcast_fn(app, workflow_id) if app else None
        run_stage(db, sr.id, broadcast_fn=broadcast_fn)
        db.commit()
        return [event_to_envelope(e) for e in e_repo.list_after(workflow_id, after_seq=before_seq, limit=100)]
    except Exception as e:
        logger.exception("[handler] apply_outline_confirm error: %s", e)
        raise
    finally:
        db.close()


def apply_section_rerun(workflow_id: uuid.UUID, ua_id: uuid.UUID, input_: dict, app: Any = None) -> list[dict]:
    """Run rerun_section logic; ua already created. Returns new event envelopes."""
    db = SessionLocal()
    try:
        w_repo = WorkflowRepository(db)
        sr_repo = StageRunRepository(db)
        ua_repo = UserActionRepository(db)
        e_repo = EventLogRepository(db)
        w = w_repo.get(workflow_id)
        if not w:
            return []
        before_seq = e_repo.max_seq(workflow_id)
        section_id = (input_ or {}).get("section_id")
        if not section_id:
            return []
        w_repo.update_status(workflow_id, WorkflowStatus.RUNNING, current_stage=GRAPH_RUN)
        attempt = sr_repo.max_attempt(workflow_id, GRAPH_RUN, scope_key=section_id) + 1
        sr = sr_repo.create(workflow_id=workflow_id, stage=GRAPH_RUN, attempt=attempt, scope_key=section_id)
        write_event(db, workflow_id, EV_STAGE_SCHEDULED, {"stage_run_id": str(sr.id), "stage": GRAPH_RUN, "scope_key": section_id, "attempt": attempt}, w.conversation_id)
        ua_repo.set_applied(ua_id)
        append_event(db, workflow_id, EV_USER_ACTION_APPLIED, {"action_id": str(ua_id), "type": "rerun_section"}, w.conversation_id)
        write_event(db, workflow_id, "graph.resumed", {"stage_run_id": str(sr.id), "resumed_from": "section_rerun"}, w.conversation_id)
        db.flush()
        broadcast_fn = _make_broadcast_fn(app, workflow_id) if app else None
        run_stage(db, sr.id, broadcast_fn=broadcast_fn)
        db.commit()
        return [event_to_envelope(e) for e in e_repo.list_after(workflow_id, after_seq=before_seq, limit=100)]
    except Exception as e:
        logger.exception("[handler] apply_section_rerun error: %s", e)
        raise
    finally:
        db.close()


def _get_ai_client() -> AIClient:
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient({
            "MODEL": settings.AI_MODEL,
            "API_KEY": settings.AI_API_KEY,
            "API_BASE": settings.AI_API_BASE,
            "TEMPERATURE": settings.AI_TEMPERATURE,
            "MAX_TOKENS": settings.AI_MAX_TOKENS,
            "TIMEOUT": settings.AI_TIMEOUT,
        })
    return _ai_client


def handle_chat_send(
    workflow_id: uuid.UUID,
    text: str,
    idempotency_key: str,
    client_msg_id: str | None = None,
) -> list[dict]:
    logger.info("[handler] handle_chat_send IN workflow_id=%s text=%r", workflow_id, text[:80] if text else "")
    db = SessionLocal()
    try:
        w_repo = WorkflowRepository(db)
        if not w_repo.get(workflow_id):
            logger.warning("[handler] workflow not found: %s", workflow_id)
            return []
        ua_repo = UserActionRepository(db)
        if ua_repo.get_by_idempotency(workflow_id, idempotency_key):
            logger.info("[handler] duplicate idempotency_key, skip: %s", idempotency_key)
            return []
        ua_repo.create(
            workflow_id=workflow_id,
            action_type="chat.send",
            payload={"text": text, "client_msg_id": client_msg_id},
            idempotency_key=idempotency_key,
        )
        e_repo = EventLogRepository(db)
        events = e_repo.list_after(workflow_id, after_seq=0, limit=50)
        messages = [{"role": "system", "content": "你是一个有帮助的AI助手，用简洁自然的语言回复用户。"}]
        for ev in events:
            if ev.type == EV_CHAT_MESSAGE and ev.payload:
                r, t = ev.payload.get("role"), ev.payload.get("text")
                if r and t and r in ("user", "assistant"):
                    messages.append({"role": r, "content": t})
        messages.append({"role": "user", "content": text})
        e1 = append_event(db, workflow_id, EV_CHAT_MESSAGE, {"role": "user", "text": text})
        logger.info("[handler] calling LLM messages_count=%d", len(messages))
        ai_client = _get_ai_client()
        reply = ai_client.chat(messages, max_tokens=1024)
        logger.info("[handler] LLM reply len=%d preview=%r", len(reply or ""), (reply or "")[:100])
        e2 = append_event(db, workflow_id, EV_CHAT_MESSAGE, {"role": "assistant", "text": reply})
        db.commit()
        logger.info("[handler] returning envelopes e1.seq=%s e2.seq=%s", e1.get("seq"), e2.get("seq"))
        return [e1, e2]
    except Exception as e:
        logger.exception("[handler] handle_chat_send error: %s", e)
        raise
    finally:
        db.close()


def handle_workflow_start(workflow_id: uuid.UUID, payload: dict, app: Any = None) -> list[dict]:
    try:
        p = WorkflowStartPayload.model_validate(payload)
    except Exception as e:
        logger.exception("[handler] workflow.start payload validation failed: %s", e)
        db = SessionLocal()
        try:
            env = append_event(
                db, workflow_id, "workflow.error",
                {"reason": str(e), "field": "payload"},
                None,
            )
            db.commit()
            return [env]
        except Exception as ex:
            logger.exception("[handler] workflow.error write failed: %s", ex)
            raise
        finally:
            db.close()

    db = SessionLocal()
    try:
        w_repo = WorkflowRepository(db)
        sr_repo = StageRunRepository(db)
        e_repo = EventLogRepository(db)
        w = w_repo.get(workflow_id)
        if not w:
            logger.warning("[handler] workflow not found: %s", workflow_id)
            return []

        if p.style not in ALLOWED_STYLES:
            env = append_event(
                db, workflow_id, "workflow.error",
                {"reason": f"invalid style: {p.style}", "field": "style"},
                w.conversation_id,
            )
            db.commit()
            return [env]
        if p.audience not in ALLOWED_AUDIENCES:
            env = append_event(
                db, workflow_id, "workflow.error",
                {"reason": f"invalid audience: {p.audience}", "field": "audience"},
                w.conversation_id,
            )
            db.commit()
            return [env]
        if not p.refs:
            env = append_event(
                db, workflow_id, "workflow.error",
                {"reason": "refs must be non-empty list[str]", "field": "refs"},
                w.conversation_id,
            )
            db.commit()
            return [env]

        params = {
            "title": p.title,
            "refs": p.refs,
            "style": p.style,
            "audience": p.audience,
            "language": p.language,
            "length": p.length,
        }
        if p.idea_id is not None:
            params["idea_id"] = p.idea_id
        w_repo.update_input_params(workflow_id, params)

        before_seq = e_repo.max_seq(workflow_id)
        append_event(
            db, workflow_id, "workflow.configured", params, w.conversation_id
        )
        initial = get_initial_stage()
        sr = sr_repo.create(workflow_id=workflow_id, stage=initial, attempt=1)
        write_event(
            db, workflow_id, EV_STAGE_SCHEDULED,
            {"stage_run_id": str(sr.id), "stage": initial},
            w.conversation_id,
        )
        db.flush()
        broadcast_fn = _make_broadcast_fn(app, workflow_id) if app else None
        run_stage(db, sr.id, broadcast_fn=broadcast_fn)
        db.commit()

        envelopes = [
            event_to_envelope(e)
            for e in e_repo.list_after(workflow_id, after_seq=before_seq, limit=100)
        ]
        return envelopes
    except Exception as e:
        logger.exception("[handler] handle_workflow_start error: %s", e)
        raise
    finally:
        db.close()
