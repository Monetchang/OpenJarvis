"""
创建 GraphRuntimeContext 的工厂，注入 core 的 append_event/save_artifact/request_user_action 实现。
"""
import uuid
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.orchestration.events import write_event
from app.orchestration.events.schema import EV_ARTIFACT_CREATED
from app.orchestration.repository import ArtifactRepository
from app.orchestration.graphs.runtime.runner import WaitUserException

from .context import GraphRuntimeContext


def create_runtime(
    db: Session,
    workflow_id: uuid.UUID,
    stage_run_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    graph_name: str,
    broadcast_fn: Callable[[dict], None] | None = None,
) -> GraphRuntimeContext:
    artifact_repo = ArtifactRepository(db)

    def _append_event(event_type: str, payload: dict, persist: bool) -> None:
        if persist:
            write_event(db, workflow_id, event_type, payload, conversation_id)
        elif broadcast_fn:
            envelope = {
                "workflow_id": str(workflow_id),
                "type": event_type,
                "payload": payload,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            broadcast_fn(envelope)

    def _save_artifact(
        artifact_type: str,
        content_json: dict | None = None,
        content_uri: str | None = None,
        scope_key: str = "global",
        title: str | None = None,
        content_preview: str | None = None,
        meta: dict | None = None,
        created_by: str = "agent",
    ) -> uuid.UUID:
        art = artifact_repo.create(
            workflow_id=workflow_id,
            artifact_type=artifact_type,
            stage_run_id=stage_run_id,
            scope_key=scope_key,
            title=title,
            content_uri=content_uri,
            content_preview=content_preview,
            content_json=content_json,
            created_by=created_by,
            meta=meta,
        )
        write_event(db, workflow_id, EV_ARTIFACT_CREATED, {"artifact_id": str(art.id), "type": art.type, "version": art.version}, conversation_id)
        return art.id

    def _request_user_action(action_required: str, payload: dict) -> None:
        raise WaitUserException(action_required, payload)

    def _load_artifacts(artifact_type: str, scope_key: str | None = None) -> list[dict]:
        arts = artifact_repo.list_by_workflow(workflow_id, artifact_type=artifact_type, scope_key=scope_key)
        by_scope: dict[str, dict] = {}
        for a in arts:
            sk = a.scope_key or "global"
            if sk not in by_scope or (by_scope[sk].get("version", 0) or 0) < (a.version or 0):
                by_scope[sk] = {"scope_key": sk, "content_json": a.content_json, "version": a.version}
        return list(by_scope.values())

    return GraphRuntimeContext(
        workflow_id=workflow_id,
        stage_run_id=stage_run_id,
        conversation_id=conversation_id,
        graph_name=graph_name,
        _append_event=_append_event,
        _save_artifact=_save_artifact,
        _request_user_action=_request_user_action,
        _load_artifacts=_load_artifacts,
    )
