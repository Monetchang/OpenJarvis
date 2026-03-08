"""
blog_graph V2 流程与各环节作用：

1. infer_style_and_audience - 根据标题推断文章类型/写作风格/目标受众，选择 prompt pack
2. fetch_and_extract_refs     - 抓取参考链接正文（trafilatura），生成 ref_cards
3. synthesize_refs           - 为每张 ref_card 提炼 key_points
4. propose_outline            - 生成 3-5 个小节大纲（id/title/description）
5. interrupt_for_outline_confirm - 等待用户确认大纲（可跳过）
6. plan_article               - 生成写作蓝图（thesis/terminology/sections_plan）
7. write_sections             - 按 plan 逐节生成 Markdown
8. assemble_article           - 拼接为完整文章（引言/总结/参考资料）
9. fact_check_and_citation_verify - 验证引用 URL 均来自 ref_cards
10. style_polish              - 术语一致性、段落结构、语气精修
11. quality_gate              - 引用数/URL 去重/模板词检查

scope_key 时: load_prior_state -> write_sections -> assemble -> fact_check -> style_polish -> quality_gate
"""
import logging
import re

from langchain_core.runnables import RunnableConfig

from app.core.ai.style_resolver import infer as infer_style_audience
from app.core.fetch_webpage import fetch_url
from app.orchestration.events.schema import EV_LLM_THINKING
from app.orchestration.graphs.runtime.runner import WaitUserException
from app.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)

QUALITY_GATE_RERUN_ACTION = "quality_gate_rerun"
FACT_CHECK_RERUN_ACTION = "fact_check_rerun"


def _get_runtime(config: RunnableConfig):
    return config.get("configurable", {}).get("runtime")


def _node_events(runtime, node: str):
    if runtime:
        runtime.append_event("node.started", {"graph": "blog", "node": node}, persist=True)

def _node_done(runtime, node: str):
    if runtime:
        runtime.append_event("node.completed", {"graph": "blog", "node": node}, persist=True)


def infer_style_and_audience(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] infer_style START - 根据标题推断文章类型/写作风格/目标受众，用于选择 prompt pack")
    runtime = _get_runtime(config)
    _node_events(runtime, "infer_style_and_audience")
    title = state.get("title") or (state.get("idea") or {}).get("body_title") or "文章"
    user_style = state.get("style")
    user_audience = state.get("audience")
    refs = state.get("refs")
    ai_client = get_ai_service().ai_client
    decision = infer_style_audience(title=title, user_style=user_style, user_audience=user_audience, refs=refs, ai_client=ai_client)
    if runtime:
        runtime.save_artifact("style_audience_decision", content_json={
            "article_type": decision.article_type,
            "style_profile": decision.style_profile,
            "audience_profile": decision.audience_profile,
            "confidence": decision.confidence,
            "decision_trace": decision.decision_trace,
        }, scope_key="global", title="Style/Audience Decision", content_preview=str(decision.decision_trace), created_by="agent")
    logger.info("[blog] infer_style END - article_type=%s style=%s audience=%s", decision.article_type, decision.style_profile, decision.audience_profile)
    _node_done(runtime, "infer_style_and_audience")
    return {
        **state,
        "article_type": decision.article_type,
        "style_profile": decision.style_profile,
        "audience_profile": decision.audience_profile,
        "style": decision.style_profile,
        "audience": decision.audience_profile,
    }


def fetch_and_extract_refs(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] fetch START - 抓取参考链接正文（trafilatura 抽取），生成 ref_cards")
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
    logger.info("[blog] fetch END - ref_cards_count=%d", len(ref_cards))
    _node_done(runtime, "fetch_and_extract_refs")
    return {**state, "ref_cards": ref_cards}


def synthesize_refs(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] synthesize START - 为每张 ref_card 提炼 key_points，供后续 outline/plan 使用")
    runtime = _get_runtime(config)
    _node_events(runtime, "synthesize_refs")
    ref_cards = state.get("ref_cards") or []
    if ref_cards:
        ref_cards = get_ai_service().synthesize_refs(ref_cards)
        if runtime:
            runtime.save_artifact("ref_cards", content_json={"ref_cards": ref_cards}, scope_key="global", title="Ref Cards", content_preview="Synthesized refs", created_by="agent")
    logger.info("[blog] synthesize END - ref_cards_count=%d", len(ref_cards))
    _node_done(runtime, "synthesize_refs")
    return {**state, "ref_cards": ref_cards}


def propose_outline(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] outline START - 根据标题与 ref_cards 生成 3-5 个小节大纲（id/title/description）")
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
            style=state.get("style") or state.get("style_profile") or "专业报告",
            audience=state.get("audience") or state.get("audience_profile") or "技术从业者",
            article_type=state.get("article_type"),
            on_thinking=_emit_thinking,
            on_thinking_chunk=_emit_thinking_chunk,
        )
        if runtime:
            aid = runtime.save_artifact("outline_plan", content_json=outline, scope_key="global", title="Outline Plan", content_preview="Proposed outline", created_by="agent")
            outline = {**outline, "_artifact_id": str(aid)}
    logger.info("[blog] outline END - sections=%s", [{"id": s.get("id"), "title": s.get("title")} for s in outline.get("sections", [])])
    _node_done(runtime, "propose_outline")
    return {**state, "outline": outline}


def interrupt_for_outline_confirm(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] interrupt START - 等待用户确认大纲，未确认则暂停（outline_confirmed=%s)", state.get("outline_confirmed"))
    runtime = _get_runtime(config)
    _node_events(runtime, "interrupt_for_outline_confirm")
    if not state.get("outline_confirmed"):
        outline = state.get("outline") or {}
        if runtime:
            runtime.request_user_action("confirm_outline", {"outline": outline, "outline_artifact_id": outline.get("_artifact_id")})
        return state
    logger.info("[blog] interrupt END - 大纲已确认，继续")
    _node_done(runtime, "interrupt_for_outline_confirm")
    return state


def plan_article(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] plan START - 根据 outline 与 ref_cards 生成写作蓝图（thesis/terminology/sections_plan）")
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
        style=state.get("style") or state.get("style_profile") or "专业报告",
        audience=state.get("audience") or state.get("audience_profile") or "技术从业者",
        article_type=state.get("article_type"),
    )
    sections_plan_by_id = {s.get("id"): s for s in article_plan.get("sections_plan", []) if s.get("id")}
    if runtime:
        runtime.save_artifact("article_plan", content_json=article_plan, scope_key="global", title="Article Plan", content_preview=article_plan.get("thesis", "")[:100], created_by="agent")
    logger.info("[blog] plan END - thesis_len=%d sections_plan=%d", len(article_plan.get("thesis", "")), len(sections_plan_by_id))
    _node_done(runtime, "plan_article")
    return {**state, "article_plan": article_plan, "sections_plan_by_id": sections_plan_by_id}


def load_prior_state(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] load_prior_state START - 单节重跑时从 artifacts 恢复 ref_cards/outline/plan/sections")
    runtime = _get_runtime(config)
    _node_events(runtime, "load_prior_state")
    out = dict(state)
    for art in runtime.load_artifacts("style_audience_decision") if runtime else []:
        cj = art.get("content_json") or {}
        if cj:
            out["article_type"] = cj.get("article_type")
            out["style_profile"] = cj.get("style_profile")
            out["audience_profile"] = cj.get("audience_profile")
            out["style"] = cj.get("style_profile")
            out["audience"] = cj.get("audience_profile")
            break
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
    logger.info("[blog] load_prior_state END - ref_cards=%d outline=%s article_plan=%s sections=%d", len(out.get("ref_cards") or []), "y" if out.get("outline") else "n", "y" if out.get("article_plan") else "n", len(out["sections"]))
    _node_done(runtime, "load_prior_state")
    return out


def write_sections(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] write_sections START - 按 sections_plan 逐节生成 Markdown，覆盖 bullet_points 并引用 recommended_refs")
    runtime = _get_runtime(config)
    _node_events(runtime, "write_sections")
    scope_key = state.get("scope_key")
    outline = state.get("outline") or {}
    ref_cards = state.get("ref_cards") or []
    sections_plan_by_id = state.get("sections_plan_by_id") or {}
    style = state.get("style") or state.get("style_profile") or "专业报告"
    audience = state.get("audience") or state.get("audience_profile") or "技术从业者"
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
            article_type=state.get("article_type"),
            on_thinking=_done_cb,
            on_thinking_chunk=_chunk_cb,
        )
        if not content.strip().startswith("#"):
            content = f"## {sec.get('title', sid)}\n\n{content}"
        logger.info("[blog] write_section sid=%s title=%s content_len=%d", sid, sec.get("title", sid), len(content))
        if runtime:
            runtime.save_artifact("section_draft", content_json={"section_id": sid, "content": content}, scope_key=sid, title=sec.get("title", sid), content_preview=content[:100], created_by="agent")
        sections_data[sid] = content
    logger.info("[blog] write_sections END - sections_count=%d", len(sections_data))
    _node_done(runtime, "write_sections")
    return {**state, "sections": sections_data}


def assemble_article(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] assemble START - 拼接各节为完整 Markdown，添加引言/总结/参考资料块")
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
    logger.info("[blog] assemble END - final_md_len=%d", len(final_md))
    _node_done(runtime, "assemble_article")
    return {**state, "sections": sections, "final_md": final_md}


def fact_check_and_citation_verify(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] fact_check START - 验证文中引用 URL 均来自 ref_cards，杜绝编造链接")
    runtime = _get_runtime(config)
    _node_events(runtime, "fact_check_and_citation_verify")
    final_md = state.get("final_md") or ""
    ref_cards = state.get("ref_cards") or []
    valid_urls = {c.get("url", "").strip() for c in ref_cards if c.get("url")}
    cited_urls = set()
    for m in re.finditer(r"\]\(([^)]+)\)", final_md):
        u = m.group(1).strip()
        if u:
            cited_urls.add(u)
    invalid = cited_urls - valid_urls
    if invalid:
        logger.warning("[blog] fact_check FAIL invalid_citations=%s", list(invalid)[:3])
        if runtime:
            runtime.append_event("fact_check.failed", {"reason": "invalid_citation", "urls": list(invalid)[:5]}, persist=True)
        raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "invalid_citation", "message": "存在未在参考资料中的引用链接"})
    kp_corpus = " ".join(
        kp.get("text", "") for c in ref_cards for kp in (c.get("key_points") or [])
    )
    eval_scores = {"citation_valid": True, "ref_urls_count": len(valid_urls), "cited_count": len(cited_urls)}
    if runtime:
        runtime.save_artifact("fact_check_scores", content_json=eval_scores, scope_key="global", title="Fact Check", content_preview=str(eval_scores), created_by="agent")
    logger.info("[blog] fact_check END - PASS %s", eval_scores)
    _node_done(runtime, "fact_check_and_citation_verify")
    return {**state, "eval_scores": eval_scores}


def style_polish(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] style_polish START - 按 style_profile 做术语一致性、段落结构、语气轻量精修")
    runtime = _get_runtime(config)
    _node_events(runtime, "style_polish")
    final_md = state.get("final_md") or ""
    style_profile = state.get("style_profile") or state.get("style") or "专业报告"
    audience_profile = state.get("audience_profile") or state.get("audience") or "技术从业者"
    if not final_md.strip():
        _node_done(runtime, "style_polish")
        return state
    polished = get_ai_service().style_polish(
        article_md=final_md,
        style_profile=style_profile,
        audience_profile=audience_profile,
    )
    if runtime:
        runtime.save_artifact("final_markdown", content_json={"markdown": polished}, scope_key="global", title="Final Markdown (polished)", content_preview=polished[:200], created_by="agent")
    logger.info("[blog] style_polish END - polished_len=%d", len(polished))
    _node_done(runtime, "style_polish")
    return {**state, "final_md": polished}


def quality_gate(state: dict, config: RunnableConfig) -> dict:
    logger.info("[blog] quality_gate START - 检查每节引用数、URL 去重、模板词黑名单")
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
    h2_blocks = re.split(r"\n##\s+", final_md)
    for i, block in enumerate(h2_blocks):
        if i == 0 and len(block.strip()) < 100:
            continue
        if len(block.strip()) > 80 and "](" not in block:
            logger.warning("[blog] quality_gate FAIL section without citation block_idx=%d", i)
            if runtime:
                runtime.append_event("quality_gate.failed", {"reason": "section_no_citation", "block_idx": i}, persist=True)
            raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "section_no_citation", "message": f"第{i+1}节缺少引用"})
    url_counts = {}
    for m in re.finditer(r"\]\(([^)]+)\)", final_md):
        u = m.group(1).strip()
        if u:
            url_counts[u] = url_counts.get(u, 0) + 1
    for url, cnt in url_counts.items():
        if cnt > 3:
            logger.warning("[blog] quality_gate FAIL url_repeated url=%s count=%d", url[:80], cnt)
            if runtime:
                runtime.append_event("quality_gate.failed", {"reason": "url_repeated", "url": url[:200], "count": cnt}, persist=True)
            raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "url_repeated", "message": f"同一链接出现{cnt}次，请分散引用"})
    for phrase, limit in [("总之", 2), ("值得注意的是", 2), ("显而易见", 1), ("毋庸置疑", 1)]:
        c = final_md.count(phrase)
        if c > limit:
            logger.warning("[blog] quality_gate FAIL template phrase=%s count=%d > %d", phrase, c, limit)
            if runtime:
                runtime.append_event("quality_gate.failed", {"reason": "template_language", "phrase": phrase, "count": c}, persist=True)
            raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "template_language", "phrase": phrase})
    for phrase in ["显然", "毋庸置疑地"]:
        if phrase in final_md:
            logger.warning("[blog] quality_gate FAIL template phrase=%s", phrase)
            if runtime:
                runtime.append_event("quality_gate.failed", {"reason": "template_language", "phrase": phrase}, persist=True)
            raise WaitUserException(QUALITY_GATE_RERUN_ACTION, {"reason": "template_language", "phrase": phrase})
    logger.info("[blog] quality_gate END - PASS")
    _node_done(runtime, "quality_gate")
    return state
