import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.orchestration.models import Artifact, ArtifactVersion


def _validate_type(name: str) -> None:
    if not name or len(name) > 64:
        raise ValueError("artifact type length must be 1-64")
    if not name.replace("_", "").isalnum():
        raise ValueError("artifact type must be alphanumeric or underscore")


class ArtifactRepository:
    def __init__(self, db: Session):
        self._db = db

    def next_version(self, workflow_id: uuid.UUID, artifact_type: str, scope_key: str = "global") -> int:
        _validate_type(artifact_type)
        row = (
            self._db.query(ArtifactVersion)
            .filter(
                and_(
                    ArtifactVersion.workflow_id == workflow_id,
                    ArtifactVersion.artifact_type == artifact_type,
                    ArtifactVersion.scope_key == scope_key,
                )
            )
            .with_for_update()
            .first()
        )
        if not row:
            row = ArtifactVersion(
                workflow_id=workflow_id,
                artifact_type=artifact_type,
                scope_key=scope_key,
                current_version=0,
            )
            self._db.add(row)
            self._db.flush()
        row.current_version += 1
        return row.current_version

    def create(
        self,
        workflow_id: uuid.UUID,
        artifact_type: str,
        stage_run_id: uuid.UUID | None = None,
        scope_key: str = "global",
        title: str | None = None,
        content_uri: str | None = None,
        content_preview: str | None = None,
        content_json: dict | None = None,
        created_by: str = "agent",
        meta: dict | None = None,
    ) -> Artifact:
        version = self.next_version(workflow_id, artifact_type, scope_key)
        a = Artifact(
            workflow_id=workflow_id,
            stage_run_id=stage_run_id,
            type=artifact_type,
            version=version,
            scope_key=scope_key,
            title=title,
            content_uri=content_uri,
            content_preview=content_preview,
            content_json=content_json,
            created_by=created_by,
            meta=meta,
        )
        self._db.add(a)
        self._db.flush()
        return a

    def get(self, artifact_id: uuid.UUID) -> Artifact | None:
        return self._db.query(Artifact).filter(Artifact.id == artifact_id).first()

    def list_by_workflow(
        self,
        workflow_id: uuid.UUID,
        artifact_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[Artifact]:
        q = self._db.query(Artifact).filter(Artifact.workflow_id == workflow_id)
        if artifact_type is not None:
            q = q.filter(Artifact.type == artifact_type)
        if scope_key is not None:
            q = q.filter(Artifact.scope_key == scope_key)
        return q.order_by(Artifact.type, Artifact.version).all()

    def get_by_version(
        self,
        workflow_id: uuid.UUID,
        artifact_type: str,
        version: int,
        scope_key: str = "global",
    ) -> Artifact | None:
        return (
            self._db.query(Artifact)
            .filter(
                and_(
                    Artifact.workflow_id == workflow_id,
                    Artifact.type == artifact_type,
                    Artifact.version == version,
                    Artifact.scope_key == scope_key,
                )
            )
            .first()
        )
