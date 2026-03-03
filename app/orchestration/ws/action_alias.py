"""Action alias mapping for action.dispatch. Maps legacy/event action names to canonical names."""

ACTION_ALIASES: dict[str, str] = {
    "confirm_outline": "outline.confirm",
    "rerun_section": "section.rerun",
}


def normalize_action(action: str | None) -> str | None:
    """Return canonical action name. If not in mapping, return original."""
    if action is None:
        return None
    return ACTION_ALIASES.get(action, action)
