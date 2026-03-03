import uuid
from dataclasses import dataclass


@dataclass
class ArtifactInput:
    artifact_type: str
    scope_key: str = "global"
    title: str | None = None
    content_uri: str | None = None
    content_preview: str | None = None
    content_json: dict | None = None
    created_by: str = "agent"
    meta: dict | None = None


@dataclass
class StageContext:
    workflow_id: uuid.UUID
    stage_run_id: uuid.UUID
    stage: str
    attempt: int
    scope_key: str | None
    input_snapshot: dict
    input_params: dict


@dataclass
class ContinueDirective:
    pass


@dataclass
class WaitUserDirective:
    action_required: str


@dataclass
class StopDirective:
    pass


@dataclass
class FailDirective:
    error_message: str


NextDirective = ContinueDirective | WaitUserDirective | StopDirective | FailDirective
