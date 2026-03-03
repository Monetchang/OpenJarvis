# Stage flow: configurable. MVP uses a simple linear chain for demo.
# Mock flow: stage_a -> stage_b -> (WAIT_USER) -> stage_c -> DONE  [DEPRECATED]
# Graph flow: GRAPH_RUN 单图执行，不再按 stage 推进

GRAPH_RUN = "GRAPH_RUN"
WAIT_USER_STAGE = "WAIT_OUTLINE_CONFIRM"
DONE_STAGE = "DONE"

# [DEPRECATED] 旧多 stage 推进，ORCHESTRATION_USE_LEGACY_STAGE_FLOW=True 时启用
MOCK_STAGE_ORDER = ["stage_a", "stage_b", WAIT_USER_STAGE, "stage_c", DONE_STAGE]


def get_initial_stage() -> str:
    from app.core.config import settings
    if getattr(settings, "ORCHESTRATION_USE_LEGACY_STAGE_FLOW", False):
        return MOCK_STAGE_ORDER[0]
    return GRAPH_RUN


def get_next_stage_after(current_stage: str) -> str | None:
    try:
        i = MOCK_STAGE_ORDER.index(current_stage)
        if i + 1 < len(MOCK_STAGE_ORDER):
            return MOCK_STAGE_ORDER[i + 1]
    except ValueError:
        pass
    return None


def is_wait_user_stage(stage: str) -> bool:
    return stage == WAIT_USER_STAGE


def is_terminal_stage(stage: str) -> bool:
    return stage == DONE_STAGE
