# Workflow orchestration: state machine, stage runs, artifacts, events, user actions

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
        model.__table__.create(engine, checkfirst=True)
