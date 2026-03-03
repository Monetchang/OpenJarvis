"""
blog_graph V2: fetch -> synthesize_refs -> propose_outline -> interrupt -> plan_article -> write_sections -> assemble_article -> quality_gate
scope_key 时: load_prior_state -> write_sections -> assemble_article -> quality_gate
"""
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from app.orchestration.graphs.nodes.blog_nodes import (
    fetch_and_extract_refs,
    synthesize_refs,
    propose_outline,
    interrupt_for_outline_confirm,
    plan_article,
    load_prior_state,
    write_sections,
    assemble_article,
    quality_gate,
)
from app.orchestration.graphs.runtime import register_graph


class BlogState(TypedDict, total=False):
    refs: list
    ref_cards: list
    idea: dict
    outline: dict
    outline_confirmed: bool
    article_plan: dict
    sections_plan_by_id: dict
    sections: dict
    final_md: str
    scope_key: str


def _route_start(state: BlogState) -> str:
    if state.get("scope_key"):
        return "load_prior_state"
    return "fetch_and_extract_refs"


def build_blog_graph() -> None:
    builder = StateGraph(BlogState)
    builder.add_node("fetch_and_extract_refs", fetch_and_extract_refs)
    builder.add_node("synthesize_refs", synthesize_refs)
    builder.add_node("propose_outline", propose_outline)
    builder.add_node("interrupt_for_outline_confirm", interrupt_for_outline_confirm)
    builder.add_node("plan_article", plan_article)
    builder.add_node("load_prior_state", load_prior_state)
    builder.add_node("write_sections", write_sections)
    builder.add_node("assemble_article", assemble_article)
    builder.add_node("quality_gate", quality_gate)
    builder.add_conditional_edges(START, _route_start, {"fetch_and_extract_refs": "fetch_and_extract_refs", "load_prior_state": "load_prior_state"})
    builder.add_edge("fetch_and_extract_refs", "synthesize_refs")
    builder.add_edge("synthesize_refs", "propose_outline")
    builder.add_edge("propose_outline", "interrupt_for_outline_confirm")
    builder.add_edge("interrupt_for_outline_confirm", "plan_article")
    builder.add_edge("plan_article", "write_sections")
    builder.add_edge("load_prior_state", "write_sections")
    builder.add_edge("write_sections", "assemble_article")
    builder.add_edge("assemble_article", "quality_gate")
    builder.add_edge("quality_gate", END)
    graph = builder.compile()
    register_graph("blog_graph", graph)
