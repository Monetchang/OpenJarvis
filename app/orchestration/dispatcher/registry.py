from typing import Callable

from .types import StageContext, ArtifactInput, NextDirective

Handler = Callable[[StageContext], tuple[list[ArtifactInput], NextDirective]]

_handlers: dict[str, Handler] = {}


def _validate_stage_name(name: str) -> None:
    if not name or len(name) > 64:
        raise ValueError("stage name length must be 1-64")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("stage name must be alphanumeric, underscore or hyphen")


def register_handler(stage_name: str, handler: Handler) -> None:
    _validate_stage_name(stage_name)
    _handlers[stage_name] = handler


def get_handler(stage_name: str) -> Handler | None:
    return _handlers.get(stage_name)
