# Workflow-level status
WorkflowStatus = type("WorkflowStatus", (), {
    "CREATED": "CREATED",
    "RUNNING": "RUNNING",
    "WAITING_USER": "WAITING_USER",
    "FAILED": "FAILED",
    "COMPLETED": "COMPLETED",
    "CANCELED": "CANCELED",
})()

# StageRun status
StageRunStatus = type("StageRunStatus", (), {
    "CREATED": "CREATED",
    "RUNNING": "RUNNING",
    "SUCCEEDED": "SUCCEEDED",
    "FAILED": "FAILED",
    "CANCELED": "CANCELED",
})()
