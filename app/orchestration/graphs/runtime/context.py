"""
GraphRuntimeContext: 封装 workflow_id、stage_run_id，持有 core 的 append_event/save_artifact/request_user_action 回调。
LangGraph 节点只能通过 runtime 与 core 交互，禁止直接写 DB 或 WS。
"""
import uuid
from dataclasses import dataclass
from typing import Callable


@dataclass
class GraphRuntimeContext:
    """由 orchestration-core 创建并注入，供 LangGraph 节点调用。"""
    workflow_id: uuid.UUID
    stage_run_id: uuid.UUID
    conversation_id: uuid.UUID | None
    graph_name: str

    # 由 core 注入的回调
    _append_event: Callable[[str, dict | None, bool], None]
    _save_artifact: Callable[..., uuid.UUID]
    _request_user_action: Callable[[str, dict], None]
    _load_artifacts: Callable[[str, str | None], list[dict]]

    def append_event(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        persist: bool = True,
    ) -> None:
        """persist=True: 落 event_logs；persist=False: 只 WS 推送不落库（如心跳）"""
        self._append_event(event_type, payload or {}, persist)

    def save_artifact(
        self,
        artifact_type: str,
        content_json: dict | None = None,
        content_uri: str | None = None,
        scope_key: str = "global",
        title: str | None = None,
        content_preview: str | None = None,
        meta: dict | None = None,
        created_by: str = "agent",
    ) -> uuid.UUID:
        """落库 artifact 并产生 artifact.created 事件，返回 artifact_id"""
        return self._save_artifact(
            artifact_type=artifact_type,
            content_json=content_json,
            content_uri=content_uri,
            scope_key=scope_key,
            title=title,
            content_preview=content_preview,
            meta=meta,
            created_by=created_by,
        )

    def request_user_action(self, action_required: str, payload: dict) -> None:
        """触发 WAITING_USER，由 core 承接：置 workflow WAITING_USER、写 stage.waiting_user"""
        self._request_user_action(action_required, payload)

    def load_artifacts(self, artifact_type: str, scope_key: str | None = None) -> list[dict]:
        """加载 artifact，latest per scope。返回 [{"scope_key":..., "content_json":..., "version":...}]"""
        return self._load_artifacts(artifact_type, scope_key)
