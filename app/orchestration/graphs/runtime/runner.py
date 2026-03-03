"""
GraphRunner: run(graph_name, input_state, runtime) -> result
"""
from dataclasses import dataclass
from typing import Any

from .context import GraphRuntimeContext

# 图注册表：graph_name -> compiled graph
_graphs: dict[str, Any] = {}


def register_graph(name: str, graph: Any) -> None:
    _graphs[name] = graph


def get_graph(name: str) -> Any | None:
    return _graphs.get(name)


@dataclass
class GraphRunResult:
    success: bool
    output_state: dict | None = None
    error: str | None = None


@dataclass
class WaitUserResult:
    action_required: str
    payload: dict


def run(
    graph_name: str,
    input_state: dict,
    runtime: GraphRuntimeContext,
) -> GraphRunResult | WaitUserResult:
    """执行图，返回 GraphRunResult 或 WaitUserResult（WAITING_USER）"""
    graph = get_graph(graph_name)
    if not graph:
        return GraphRunResult(success=False, error=f"graph '{graph_name}' not found")
    config = {"configurable": {"runtime": runtime}}
    try:
        output = graph.invoke(input_state, config=config)
        return GraphRunResult(success=True, output_state=output)
    except WaitUserException as e:
        return WaitUserResult(action_required=e.action_required, payload=e.payload)
    except Exception as e:
        return GraphRunResult(success=False, error=str(e))


class WaitUserException(Exception):
    """request_user_action 的 core 实现抛出此类以中断图执行"""
    def __init__(self, action_required: str, payload: dict):
        self.action_required = action_required
        self.payload = payload


class GraphRunner:
    @staticmethod
    def run(
        graph_name: str,
        input_state: dict,
        runtime: GraphRuntimeContext,
    ) -> GraphRunResult | WaitUserResult:
        return run(graph_name, input_state, runtime)
