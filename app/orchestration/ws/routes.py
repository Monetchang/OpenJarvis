import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.database import SessionLocal
from app.orchestration.repository import WorkflowRepository
from app.orchestration.ws.action_alias import normalize_action
from app.orchestration.ws.handlers import (
    handle_chat_send,
    handle_workflow_start,
    try_accept_workflow_start,
    try_accept_outline_confirm,
    try_accept_section_rerun,
    apply_outline_confirm,
    apply_section_rerun,
    write_action_ack_event,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/workflows/{workflow_id}")
async def ws_workflow(websocket: WebSocket, workflow_id: uuid.UUID):
    await websocket.accept()
    db = SessionLocal()
    try:
        w_repo = WorkflowRepository(db)
        if not w_repo.get(workflow_id):
            await websocket.close(code=4404)
            return
    finally:
        db.close()

    broadcaster = getattr(websocket.app.state, "ws_broadcaster", None)
    if broadcaster:
        key = str(workflow_id)
        broadcaster.subscribe(key, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                continue
            msg_type = data.get("type")
            payload = data.get("payload") or {}

            if msg_type == "workflow.start":
                data = {
                    "type": "action.dispatch",
                    "payload": {"action": "workflow.start", "input": payload},
                    "meta": {"idempotency_key": payload.get("idempotency_key") or str(uuid.uuid4())},
                }
                msg_type = "action.dispatch"
                payload = data["payload"]

            if msg_type == "action.dispatch":
                meta = data.get("meta") or {}
                action = payload.get("action")
                action = normalize_action(action)
                if payload.get("action") and action != payload.get("action"):
                    logger.info("[WS] action alias mapped alias=%s canonical=%s", payload.get("action"), action)
                input_ = payload.get("input") or {}
                idempotency_key = meta.get("idempotency_key")
                extra_payload = None
                if not idempotency_key:
                    status, reason = "REJECTED", "idempotency_key required"
                    action_id = None
                    extra_payload = None
                elif action == "workflow.start":
                    loop = asyncio.get_running_loop()
                    status, _seq, action_id, reason, extra_payload = await loop.run_in_executor(
                        None,
                        lambda: try_accept_workflow_start(workflow_id, idempotency_key, input_),
                    )
                elif action == "outline.confirm":
                    loop = asyncio.get_running_loop()
                    status, _seq, action_id, reason = await loop.run_in_executor(
                        None,
                        lambda: try_accept_outline_confirm(workflow_id, idempotency_key, input_),
                    )
                    extra_payload = None
                elif action == "section.rerun":
                    loop = asyncio.get_running_loop()
                    status, _seq, action_id, reason = await loop.run_in_executor(
                        None,
                        lambda: try_accept_section_rerun(workflow_id, idempotency_key, input_),
                    )
                    extra_payload = None
                else:
                    status, reason = "REJECTED", "unknown action"
                    action_id = None
                    extra_payload = None
                ack_payload = {
                    "action": action or "",
                    "idempotency_key": idempotency_key or "",
                    "status": status,
                    "action_id": str(action_id) if action_id is not None else str(uuid.uuid4()),
                    "reason": reason,
                }
                if extra_payload:
                    ack_payload.update(extra_payload)
                loop = asyncio.get_running_loop()
                ack_env = await loop.run_in_executor(
                    None,
                    lambda: write_action_ack_event(workflow_id, ack_payload),
                )
                envelopes = [ack_env]
                if status == "ACCEPTED" and action == "workflow.start":
                    loop = asyncio.get_running_loop()
                    try:
                        extra = await loop.run_in_executor(
                            None, lambda: handle_workflow_start(workflow_id, input_, app=websocket.app)
                        )
                        envelopes.extend(extra)
                    except Exception as e:
                        logger.exception("[WS] action.dispatch workflow.start failed: %s", e)
                elif status == "ACCEPTED" and action == "outline.confirm" and action_id is not None:
                    loop = asyncio.get_running_loop()
                    try:
                        extra = await loop.run_in_executor(
                            None, lambda: apply_outline_confirm(workflow_id, action_id, input_, app=websocket.app)
                        )
                        envelopes.extend(extra)
                    except Exception as e:
                        logger.exception("[WS] action.dispatch outline.confirm failed: %s", e)
                elif status == "ACCEPTED" and action == "section.rerun" and action_id is not None:
                    loop = asyncio.get_running_loop()
                    try:
                        extra = await loop.run_in_executor(
                            None, lambda: apply_section_rerun(workflow_id, action_id, input_, app=websocket.app)
                        )
                        envelopes.extend(extra)
                    except Exception as e:
                        logger.exception("[WS] action.dispatch section.rerun failed: %s", e)
            elif msg_type == "chat.send":
                text = payload.get("text")
                idempotency_key = payload.get("idempotency_key")
                if not text or not idempotency_key:
                    logger.warning("[WS] chat.send missing text/idempotency_key: %s", payload)
                    continue
                logger.info("[WS] chat.send IN workflow_id=%s text=%r", workflow_id, text[:80])
                loop = asyncio.get_running_loop()
                envelopes = await loop.run_in_executor(
                    None,
                    lambda: handle_chat_send(
                        workflow_id,
                        text,
                        idempotency_key,
                        payload.get("client_msg_id"),
                    ),
                )
                logger.info("[WS] chat.send OUT workflow_id=%s envelopes_count=%d", workflow_id, len(envelopes))
            else:
                if msg_type:
                    logger.warning("[WS] unknown message type: %s", msg_type)
                continue

            for i, env in enumerate(envelopes):
                msg = json.dumps(env)
                try:
                    await websocket.send_text(msg)
                    logger.info("[WS] sent envelope[%d] seq=%s type=%s to websocket", i, env.get("seq"), env.get("type"))
                except Exception as e:
                    logger.error("[WS] send_text failed: %s", e)
                if broadcaster:
                    await broadcaster.broadcast(key, env)
    except WebSocketDisconnect:
        pass
    finally:
        if broadcaster:
            broadcaster.unsubscribe(str(workflow_id), websocket)
