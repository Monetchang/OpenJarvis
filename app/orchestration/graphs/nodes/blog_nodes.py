"""
blog_graph V2: fetch -> synthesize_refs -> propose_outline -> interrupt -> plan_article -> write_sections -> assemble_article -> quality_gate
scope_key 时: load_prior_state -> write_sections -> assemble_article -> quality_gate
"""
import logging

from langchain_core.runnables import RunnableConfig

from app.core.fetch_webpage import fetch_url
from app.orchestration.events.schema import EV_LLM_THINKING
from app.orchestration.graphs.runtime.runner import WaitUserException
from app.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)

QUALITY_GATE_RERUN_ACTION = "quality_gate_rerun"


def _get_runtime(config: RunnableConfig):
    return config.get("configurable", {}).get("runtime")


def _node_events(runtime, node: str):
    if runtime:
        runtime.append_event("node.started", {"graph": "blog", "node": node}, persist=True)

def _node_done(runtime, node: str):
    if runtime:
        runtime.append_event("node.completed", {"graph": "blog", "node": node}, persist=True)


def fetch_and_extract_refs(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "fetch_and_extract_refs")
    refs = state.get("refs") or []
    ref_cards = []
    if isinstance(refs, list):
        for i, r in enumerate(refs):
            ref_id = f"r{i + 1}"
            if isinstance(r, str):
                card = fetch_url(r)
                ref_cards.append({
                    "ref_id": ref_id,
                    "url": card["url"],
                    "title": card["title"],
                    "summary": card["summary"],
                })
                logger.info(
                    "[blog] ref_card ref_id=%s url=%s title=%s summary_preview=%s",
                    ref_id, card["url"], (card["title"] or "")[:60], (card["summary"] or "")[:100],
                )
            else:
                ref_cards.append({"ref_id": ref_id, "url": str(r), "title": str(r), "summary": ""})
    logger.info("[blog] fetch_and_extract_refs done ref_cards_count=%d", len(ref_cards))
    _node_done(runtime, "fetch_and_extract_refs")
    return {**state, "ref_cards": ref_cards}


def synthesize_refs(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "synthesize_refs")
    ref_cards = state.get("ref_cards") or []
    if ref_cards:
        ref_cards = get_ai_service().synthesize_refs(ref_cards)
        if runtime:
            runtime.save_artifact("ref_cards", content_json={"ref_cards": ref_cards}, scope_key="global", title="Ref Cards", content_preview="Synthesized refs", created_by="agent")
    logger.info("[blog] synthesize_refs done ref_cards_count=%d", len(ref_cards))
    _node_done(runtime, "synthesize_refs")
    return {**state, "ref_cards": ref_cards}


def propose_outline(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "propose_outline")
    title = state.get("title") or (state.get("idea") or {}).get("body_title") or "文章"
    logger.info("[blog] propose_outline title=%r state_title=%r", title, state.get("title"))
    ref_cards = state.get("ref_cards") or []
    if state.get("outline_confirmed") and state.get("outline"):
        outline = state["outline"]
    else:
        def _emit_thinking_chunk(chunk: str) -> None:
            if runtime and chunk:
                runtime.append_event(EV_LLM_THINKING, {"node": "propose_outline", "chunk": chunk}, persist=False)
        def _emit_thinking(t: str) -> None:
            if runtime and t:
                logger.info("[blog] llm.thinking node=propose_outline len=%d", len(t))
                runtime.append_event(EV_LLM_THINKING, {"node": "propose_outline", "thinking": t}, persist=True)
        outline = get_ai_service().generate_blog_outline(
            title, ref_cards,
            style=state.get("style") or "专业报告",
            audience=state.get("audience") or "技术从业者",
            on_thinking=_emit_thinking,
            on_thinking_chunk=_emit_thinking_chunk,
        )
        if runtime:
            aid = runtime.save_artifact("outline_plan", content_json=outline, scope_key="global", title="Outline Plan", content_preview="Proposed outline", created_by="agent")
            outline = {**outline, "_artifact_id": str(aid)}
    logger.info("[blog] propose_outline sections=%s", [{"id": s.get("id"), "title": s.get("title"), "description": s.get("description", "")[:50]} for s in outline.get("sections", [])])
    _node_done(runtime, "propose_outline")
    return {**state, "outline": outline}


def interrupt_for_outline_confirm(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "interrupt_for_outline_confirm")
    if not state.get("outline_confirmed"):
        outline = state.get("outline") or {}
        if runtime:
            runtime.request_user_action("confirm_outline", {"outline": outline, "outline_artifact_id": outline.get("_artifact_id")})
        return state
    _node_done(runtime, "interrupt_for_outline_confirm")
    return state


def plan_article(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "plan_article")
    title = state.get("title") or (state.get("idea") or {}).get("body_title") or "文章"
    logger.info("[blog] plan_article title=%r state_title=%r", title, state.get("title"))
    ref_cards = state.get("ref_cards") or []
    outline = state.get("outline") or {}
    article_plan = get_ai_service().plan_article(
        title=title,
        ref_cards=ref_cards,
        outline=outline,
        style=state.get("style") or "专业报告",
        audience=state.get("audience") or "技术从业者",
    )
    sections_plan_by_id = {s.get("id"): s for s in article_plan.get("sections_plan", []) if s.get("id")}
    if runtime:
        runtime.save_artifact("article_plan", content_json=article_plan, scope_key="global", title="Article Plan", content_preview=article_plan.get("thesis", "")[:100], created_by="agent")
    logger.info("[blog] plan_article thesis_len=%d sections_plan=%d", len(article_plan.get("thesis", "")), len(sections_plan_by_id))
    _node_done(runtime, "plan_article")
    return {**state, "article_plan": article_plan, "sections_plan_by_id": sections_plan_by_id}


def load_prior_state(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "load_prior_state")
    out = dict(state)
    for art in runtime.load_artifacts("ref_cards") if runtime else []:
        cj = art.get("content_json") or {}
        if cj.get("ref_cards") is not None:
            out["ref_cards"] = cj["ref_cards"]
            break
    for art in runtime.load_artifacts("outline_plan") if runtime else []:
        cj = art.get("content_json") or {}
        if cj:
            out["outline"] = cj
            break
    for art in runtime.load_artifacts("article_plan") if runtime else []:
        cj = art.get("content_json") or {}
        if cj:
            out["article_plan"] = cj
            out["sections_plan_by_id"] = {s.get("id"): s for s in cj.get("sections_plan", []) if s.get("id")}
            break
    if state.get("scope_key") and runtime:
        for art in runtime.load_artifacts("section_draft"):
            cj = art.get("content_json") or {}
            sid = cj.get("section_id") or art.get("scope_key")
            if sid:
                out.setdefault("sections", {})[sid] = cj.get("content", "")
    sections = out.get("sections") or {}
    out["sections"] = dict(sections)
    logger.info("[blog] load_prior_state ref_cards=%d outline=%s article_plan=%s sections=%d", len(out.get("ref_cards") or []), "y" if out.get("outline") else "n", "y" if out.get("article_plan") else "n", len(out["sections"]))
    _node_done(runtime, "load_prior_state")
    return out


def write_sections(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "write_sections")
    scope_key = state.get("scope_key")
    outline = state.get("outline") or {}
    ref_cards = state.get("ref_cards") or []
    sections_plan_by_id = state.get("sections_plan_by_id") or {}
    style = state.get("style") or "专业报告"
    audience = state.get("audience") or "技术从业者"
    sections_data = dict(state.get("sections") or {})
    ai = get_ai_service()
    article_title = state.get("title") or ""
    logger.info("[blog] write_sections article_title=%r state_title=%r", article_title, state.get("title"))
    for sec in outline.get("sections", []):
        sid = sec.get("id", f"s{len(sections_data)}")
        if scope_key and sid != scope_key:
            continue
        section_plan = sections_plan_by_id.get(sid) or {}
        section_goal = section_plan.get("goal") or sec.get("description", "")
        bullet_points = section_plan.get("bullet_points") or []
        recommended_refs = section_plan.get("recommended_refs") or []
        target_length = max(800, int(section_plan.get("target_length", 800)))

        def _emit_section_thinking(section_id: str):
            def _chunk_cb(chunk: str) -> None:
                if runtime and chunk:
                    runtime.append_event(EV_LLM_THINKING, {"node": "write_sections", "section_id": section_id, "chunk": chunk}, persist=False)
            def _done_cb(t: str) -> None:
                if runtime and t:
                    logger.info("[blog] llm.thinking node=write_sections section_id=%s len=%d", section_id, len(t))
                    runtime.append_event(EV_LLM_THINKING, {"node": "write_sections", "section_id": section_id, "thinking": t}, persist=True)
            return _chunk_cb, _done_cb
        _chunk_cb, _done_cb = _emit_section_thinking(sid)
        content = ai.generate_blog_section(
            section_title=sec.get("title", sid),
            section_goal=section_goal,
            bullet_points=bullet_points,
            recommended_refs=recommended_refs,
            target_length=target_length,
            ref_cards=ref_cards,
            style=style,
            audience=audience,
            article_title=article_title,
            on_thinking=_done_cb,
            on_thinking_chunk=_chunk_cb,
        )
        if not content.strip().startswith("#"):
            content = f"## {sec.get('title', sid)}\n\n{content}"
        logger.info("[blog] write_section sid=%s title=%s content_len=%d", sid, sec.get("title", sid), len(content))
        if runtime:
            runtime.save_artifact("section_draft", content_json={"section_id": sid, "content": content}, scope_key=sid, title=sec.get("title", sid), content_preview=content[:100], created_by="agent")
        sections_data[sid] = content
    _node_done(runtime, "write_sections")
    return {**state, "sections": sections_data}


def assemble_article(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "assemble_article")
    sections = {}
    if state.get("scope_key") and runtime:
        for art in runtime.load_artifacts("section_draft"):
            cj = art.get("content_json") or {}
            sid = cj.get("section_id") or art.get("scope_key")
            if sid:
                sections[sid] = cj.get("content", "")
    sections.update(state.get("sections") or {})
    parts = [sections[k] for k in sorted(sections.keys())]
    body_md = "\n\n".join(parts) if parts else ""
    article_plan = state.get("article_plan") or {}
    thesis = article_plan.get("thesis", "")
    title = state.get("title") or "文章"
    ref_cards = state.get("ref_cards") or []
    intro = f"本文围绕「{thesis}」展开讨论。\n\n" if thesis else ""
    conclusion = f"\n\n---\n\n## 总结\n\n综上，{thesis}\n\n" if thesis else ""
    refs_block = "\n\n## 参考资料\n\n" + "\n".join(f"- [{c.get('title', '')}]({c.get('url', '')})" for c in ref_cards if c.get("url")) if ref_cards else ""
    final_md = f"# {title}\n\n{intro}{body_md}{conclusion}{refs_block}"
    if runtime:
        runtime.save_artifact("final_markdown", content_json={"markdown": final_md}, scope_key="global", title="Final Markdown", content_preview=final_md[:200], created_by="agent")
    logger.info("[blog] assemble_article final_md_len=%d", len(final_md))
    _node_done(runtime, "assemble_article")
    return {**state, "sections": sections, "final_md": final_md}


def quality_gate(state: dict, config: RunnableConfig) -> dict:
    runtime = _get_runtime(config)
    _node_events(runtime, "quality_gate")
    final_md = state.get("final_md") or ""
    sections = state.get("sections") or {}
    n_sections = len(sections)
    citation_count = final_md.count("](")
    if n_sections > 0 and citation_count < n_sections:
        logger.warning("[blog] quality_gate FAIL citation_count=%d < sections=%d", citation_count, n_sections)
        if runtime:
            runtime.append_event("quality_gate.failed", {"reason": "citation_count", "citation_count": citation_count, "sections_count": n_sections}, persist=True)
        raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "citation_count", "message": f"引用数{citation_count}少于节数{n_sections}"})
    for phrase, limit in [("总之", 2), ("值得注意的是", 2)]:
        c = final_md.count(phrase)
        if c > limit:
            logger.warning("[blog] quality_gate FAIL template phrase=%s count=%d > %d", phrase, c, limit)
            if runtime:
                runtime.append_event("quality_gate.failed", {"reason": "template_language", "phrase": phrase, "count": c}, persist=True)
            raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "template_language", "phrase": phrase})
    if "显然" in final_md:
        logger.warning("[blog] quality_gate FAIL template phrase=显然")
        if runtime:
            runtime.append_event("quality_gate.failed", {"reason": "template_language", "phrase": "显然"}, persist=True)
        raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "template_language", "phrase": "显然"})
    logger.info("[blog] quality_gate PASS")
    _node_done(runtime, "quality_gate")
    return state
