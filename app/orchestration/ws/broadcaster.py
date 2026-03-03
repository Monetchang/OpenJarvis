import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventBroadcaster:
    def __init__(self):
        self._subs: dict[str, set[WebSocket]] = {}

    def subscribe(self, workflow_id: str, ws: WebSocket) -> None:
        if workflow_id not in self._subs:
            self._subs[workflow_id] = set()
        self._subs[workflow_id].add(ws)

    def unsubscribe(self, workflow_id: str, ws: WebSocket) -> None:
        s = self._subs.get(workflow_id)
        if s:
            s.discard(ws)
            if not s:
                del self._subs[workflow_id]

    async def broadcast(self, workflow_id: str, envelope: dict[str, Any]) -> None:
        key = workflow_id if isinstance(workflow_id, str) else str(workflow_id)
        s = self._subs.get(key)
        if not s:
            return
        dead = set()
        msg = json.dumps(envelope)
        for ws in s:
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning("broadcast send failed for workflow %s: %s", key, e)
                dead.add(ws)
        for ws in dead:
            s.discard(ws)
