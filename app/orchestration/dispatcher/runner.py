import asyncio
import uuid
from typing import Callable

from sqlalchemy.orm import Session

from app.orchestration.repository import (
    WorkflowRepository,
    StageRunRepository,
    ArtifactRepository,
)
from app.orchestration.events import (
    write_event,
    EV_STAGE_STARTED,
    EV_STAGE_COMPLETED,
    EV_STAGE_FAILED,
    EV_ARTIFACT_CREATED,
    EV_STAGE_WAITING_USER,
    EV_STAGE_SCHEDULED,
)
from app.orchestration.fsm import (
    WorkflowStatus,
    get_next_stage_after,
    is_terminal_stage,
    ensure_no_running_stage,
    GRAPH_RUN,
)
from app.orchestration.dispatcher.registry import get_handler
from app.orchestration.dispatcher.types import (
    StageContext,
    WaitUserDirective,
    FailDirective,
    StopDirective,
)
from app.orchestration.graphs.runtime import GraphRunner, GraphRunResult, WaitUserResult
from app.orchestration.graphs.runtime.factory import create_runtime


GRAPH_NAME = "blog_graph"


def _run_graph_stage(db: Session, sr, w, broadcast_fn: Callable[[dict], None] | None = None) -> None:
    stage_repo = StageRunRepository(db)
    workflow_repo = WorkflowRepository(db)
    artifact_repo = ArtifactRepository(db)
    write_event(db, sr.workflow_id, "graph.started", {"graph": GRAPH_NAME, "workflow_id": str(sr.workflow_id), "stage_run_id": str(sr.id)}, w.conversation_id)
    runtime = create_runtime(db, sr.workflow_id, sr.id, w.conversation_id, GRAPH_NAME, broadcast_fn=broadcast_fn)
    input_state = dict(w.input_params or {})
    if sr.scope_key:
        input_state["scope_key"] = sr.scope_key
    result = GraphRunner.run(GRAPH_NAME, input_state, runtime)

    if isinstance(result, GraphRunResult):
        if result.success:
            artifact_ids = [a.id for a in artifact_repo.list_by_workflow(sr.workflow_id) if a.stage_run_id == sr.id]
            stage_repo.set_succeeded(sr.id, output_artifact_ids=artifact_ids)
            write_event(db, sr.workflow_id, "graph.completed", {"graph": GRAPH_NAME, "workflow_id": str(sr.workflow_id), "stage_run_id": str(sr.id)}, w.conversation_id)
            workflow_repo.update_status(sr.workflow_id, WorkflowStatus.COMPLETED, current_stage="DONE")
        else:
            stage_repo.set_failed(sr.id, result.error or "unknown")
            write_event(db, sr.workflow_id, "graph.failed", {"graph": GRAPH_NAME, "workflow_id": str(sr.workflow_id), "stage_run_id": str(sr.id), "error": result.error}, w.conversation_id)
            workflow_repo.update_status(sr.workflow_id, WorkflowStatus.FAILED, error_message=result.error)
    elif isinstance(result, WaitUserResult):
        artifact_ids = [a.id for a in artifact_repo.list_by_workflow(sr.workflow_id) if a.stage_run_id == sr.id]
        stage_repo.set_succeeded(sr.id, output_artifact_ids=artifact_ids)
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.WAITING_USER, current_stage="WAIT_OUTLINE_CONFIRM")
        write_event(db, sr.workflow_id, EV_STAGE_WAITING_USER, {"action_required": result.action_required, "payload": result.payload}, w.conversation_id)


def run_stage(db: Session, stage_run_id: uuid.UUID, broadcast_fn: Callable[[dict], None] | None = None) -> None:
    stage_repo = StageRunRepository(db)
    workflow_repo = WorkflowRepository(db)
    artifact_repo = ArtifactRepository(db)

    sr = stage_repo.get_for_update(stage_run_id)
    if not sr or sr.status != "CREATED":
        return
    ensure_no_running_stage(db, sr.workflow_id)

    w = workflow_repo.get(sr.workflow_id)
    if not w:
        return
    workflow_repo.update_status(sr.workflow_id, WorkflowStatus.RUNNING, current_stage=sr.stage)
    stage_repo.set_running(stage_run_id)
    db.flush()

    write_event(db, sr.workflow_id, EV_STAGE_STARTED, {"stage_run_id": str(sr.id), "stage": sr.stage}, w.conversation_id)

    if sr.stage == GRAPH_RUN:
        _run_graph_stage(db, sr, w, broadcast_fn=broadcast_fn)
        return

    handler = get_handler(sr.stage)
    if not handler:
        stage_repo.set_failed(stage_run_id, f"no handler for stage {sr.stage}")
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.FAILED, error_message=f"no handler for {sr.stage}")
        write_event(db, sr.workflow_id, EV_STAGE_FAILED, {"stage_run_id": str(sr.id), "stage": sr.stage, "error": f"no handler for {sr.stage}"}, w.conversation_id)
        return

    ctx = StageContext(
        workflow_id=sr.workflow_id,
        stage_run_id=sr.id,
        stage=sr.stage,
        attempt=sr.attempt,
        scope_key=sr.scope_key,
        input_snapshot=sr.input_snapshot or {},
        input_params=w.input_params or {},
    )
    try:
        artifacts_in, directive = handler(ctx)
    except Exception as e:
        stage_repo.set_failed(stage_run_id, str(e))
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.FAILED, error_message=str(e))
        write_event(db, sr.workflow_id, EV_STAGE_FAILED, {"stage_run_id": str(sr.id), "stage": sr.stage, "error": str(e)}, w.conversation_id)
        return

    if isinstance(directive, FailDirective):
        stage_repo.set_failed(stage_run_id, directive.error_message)
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.FAILED, error_message=directive.error_message)
        write_event(db, sr.workflow_id, EV_STAGE_FAILED, {"stage_run_id": str(sr.id), "stage": sr.stage, "error": directive.error_message}, w.conversation_id)
        return

    artifact_ids: list[uuid.UUID] = []
    for ain in artifacts_in or []:
        art = artifact_repo.create(
            workflow_id=sr.workflow_id,
            artifact_type=ain.artifact_type,
            stage_run_id=sr.id,
            scope_key=ain.scope_key,
            title=ain.title,
            content_uri=ain.content_uri,
            content_preview=ain.content_preview,
            content_json=ain.content_json,
            created_by=ain.created_by,
            meta=ain.meta,
        )
        artifact_ids.append(art.id)
        write_event(
            db,
            sr.workflow_id,
            EV_ARTIFACT_CREATED,
            {"artifact_id": str(art.id), "type": art.type, "version": art.version},
            w.conversation_id,
        )

    stage_repo.set_succeeded(stage_run_id, output_artifact_ids=artifact_ids)
    write_event(db, sr.workflow_id, EV_STAGE_COMPLETED, {"stage_run_id": str(sr.id), "stage": sr.stage}, w.conversation_id)

    if isinstance(directive, WaitUserDirective):
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.WAITING_USER, current_stage="WAIT_OUTLINE_CONFIRM")
        write_event(
            db,
            sr.workflow_id,
            EV_STAGE_WAITING_USER,
            {"action_required": directive.action_required},
            w.conversation_id,
        )
        return

    if isinstance(directive, StopDirective):
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.COMPLETED, current_stage="DONE")
        return

    next_stage = get_next_stage_after(sr.stage)
    if next_stage and is_terminal_stage(next_stage):
        workflow_repo.update_status(sr.workflow_id, WorkflowStatus.COMPLETED, current_stage=next_stage)
        return
    if next_stage:
        schedule_next_stage(db, sr.workflow_id, next_stage, w.conversation_id, broadcast_fn=broadcast_fn)


def schedule_next_stage(db: Session, workflow_id: uuid.UUID, stage: str, conversation_id: uuid.UUID | None = None, broadcast_fn: Callable[[dict], None] | None = None) -> None:
    ensure_no_running_stage(db, workflow_id)
    stage_repo = StageRunRepository(db)
    workflow_repo = WorkflowRepository(db)
    attempt = stage_repo.max_attempt(workflow_id, stage) + 1
    sr = stage_repo.create(workflow_id=workflow_id, stage=stage, attempt=attempt)
    write_event(
        db,
        workflow_id,
        EV_STAGE_SCHEDULED,
        {"stage_run_id": str(sr.id), "stage": stage, "attempt": attempt},
        conversation_id,
    )
    db.flush()
    run_stage(db, sr.id, broadcast_fn=broadcast_fn)
