# Workflow orchestration: state machine, stage runs, artifacts, events, user actions
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


def create_tables(engine):
    """Create orchestration tables. Call at app startup."""
    from app.orchestration.models import (
        Conversation,
        Workflow,
        StageRun,
        Artifact,
        ArtifactVersion,
        EventLog,
        UserAction,
    )
    for model in (Conversation, Workflow, StageRun, Artifact, ArtifactVersion, EventLog, UserAction):
        try:
            model.__table__.create(engine, checkfirst=True)
        except IntegrityError as e:
            err_str = str(e.orig).lower()
            if "pg_type_typname_nsp_index" in err_str or ("duplicate key" in err_str and "already exists" in err_str):
                try:
                    with engine.connect() as conn:
                        conn.execute(text(f"DROP TYPE IF EXISTS {model.__tablename__} CASCADE"))
                        conn.commit()
                    model.__table__.create(engine, checkfirst=True)
                except Exception as ex:
                    logger.warning("Table %s create retry failed: %s", model.__tablename__, ex)
            else:
                raise
