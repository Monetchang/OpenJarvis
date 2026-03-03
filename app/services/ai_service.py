# coding=utf-8
"""
AI 服务层

封装 AI 翻译和选题生成功能
"""
import importlib
import json
import logging
import re
from typing import List, Optional, Dict, Any, Callable
from app.core.config import settings
from app.core.ai import AIClient, AITranslator, MTTranslator, BlogTopicsGenerator, TranslationResult, BatchTranslationResult, BlogTopicsResult

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务"""

    def __init__(self):
        """初始化 AI 服务"""
        # AI 配置
        self.ai_config = {
            "MODEL": settings.AI_MODEL,
            "API_KEY": settings.AI_API_KEY,
            "API_BASE": settings.AI_API_BASE,
            "TEMPERATURE": settings.AI_TEMPERATURE,
            "MAX_TOKENS": settings.AI_MAX_TOKENS,
            "TIMEOUT": settings.AI_TIMEOUT,
        }

        # 翻译配置
        self.translation_config = {
            "ENABLED": settings.TRANSLATION_ENABLED,
            "LANGUAGE": settings.TRANSLATION_LANGUAGE,
            "PROMPT_MODULE": "ai_translation_prompt",
        }

        # 翻译实现：mt=免费机器翻译, ai=LLM
        use_mt = (settings.TRANSLATION_PROVIDER or "mt").lower() == "mt"
        self.translator = (
            MTTranslator(self.translation_config)
            if use_mt and settings.TRANSLATION_ENABLED
            else (AITranslator(self.translation_config, self.ai_config) if settings.TRANSLATION_ENABLED else None)
        )

        # 选题配置
        self.topics_config = {
            "ENABLED": settings.TOPICS_ENABLED,
            "MIN_TOPICS": settings.TOPICS_MIN_COUNT,
            "MAX_TOPICS": settings.TOPICS_MAX_COUNT,
            "PROMPT_MODULE": "ai_blog_topics_prompt",
            "INCLUDE_PLATFORMS": False,
            "INCLUDE_RSS": True,
            "MAX_NEWS_FOR_GENERATION": 100,
        }

        # 初始化组件
        self.ai_client = AIClient(self.ai_config)
        self.topic_generator = BlogTopicsGenerator(self.topics_config, self.ai_config) if settings.TOPICS_ENABLED else None

    def translate_text(self, text: str) -> TranslationResult:
        """
        翻译单条文本

        Args:
            text: 要翻译的文本

        Returns:
            TranslationResult: 翻译结果
        """
        if not self.translator:
            result = TranslationResult(original_text=text, error="翻译功能未启用")
            return result

        return self.translator.translate(text)

    def translate_batch(self, texts: List[str]) -> BatchTranslationResult:
        """
        批量翻译文本

        Args:
            texts: 要翻译的文本列表

        Returns:
            BatchTranslationResult: 批量翻译结果
        """
        if not self.translator:
            result = BatchTranslationResult(total_count=len(texts))
            for text in texts:
                result.results.append(TranslationResult(original_text=text, error="翻译功能未启用"))
            result.fail_count = len(texts)
            return result

        return self.translator.translate_batch(texts)

    def generate_topics(
        self,
        rss_items: List[Dict[str, Any]],
        additional_news: Optional[List[Dict]] = None
    ) -> BlogTopicsResult:
        """
        生成博客选题

        Args:
            rss_items: RSS 条目列表（字典格式）
            additional_news: 额外的新闻数据（可选）

        Returns:
            BlogTopicsResult: 选题生成结果
        """
        if not self.topic_generator:
            result = BlogTopicsResult()
            result.error = "选题生成功能未启用"
            return result

        # 转换为字典格式（索引作为键）
        rss_dict = {i: item for i, item in enumerate(rss_items)}

        return self.topic_generator.generate(
            platforms_news=additional_news or [],
            rss_items=rss_dict,
            standalone_data=None
        )

    def generate_article(
        self,
        title: str,
        style: str,
        audience: str,
        length: str = "medium",
        language: str = "zh-CN",
        related_articles: list = None
    ) -> str:
        """
        生成文章

        Args:
            title: 文章标题/选题
            style: 写作风格
            audience: 目标人群
            length: 文章长度
            language: 输出语言
            related_articles: 选题关联的参考文章 [{"title","url","source"}]
        """
        length_map = {"short": "800-1500字", "medium": "1500-3000字", "long": "3000-5000字"}
        refs_text = ""
        if related_articles:
            refs_text = "\n参考资料（请结合以下内容撰写，可引用并标注来源）：\n"
            for i, r in enumerate(related_articles, 1):
                refs_text += f"{i}. {r.get('title','')} - {r.get('url','')}\n"

        prompt = self._load_article_prompt().format(
            title=title,
            refs_text=refs_text,
            style=style,
            audience=audience,
            length_desc=length_map.get(length, "1500-3000字"),
            language_desc="中文" if language == "zh-CN" else "英文",
        )
        messages = [{"role": "user", "content": prompt}]
        return self.ai_client.chat(messages)

    def _load_prompt(self, module_name: str) -> str:
        """从 app.core.prompts 加载 prompt 模块的 TEMPLATE"""
        try:
            mod = importlib.import_module(f"app.core.prompts.{module_name}")
            return getattr(mod, "TEMPLATE", "")
        except Exception:
            return ""

    def _load_article_prompt(self) -> str:
        """加载文章生成 prompt"""
        return self._load_prompt(settings.AI_ARTICLE_PROMPT_MODULE)

    def generate_blog_outline(
        self,
        title: str,
        ref_cards: List[Dict[str, Any]],
        style: str = "专业报告",
        audience: str = "技术从业者",
        on_thinking: Optional[Callable[[str], None]] = None,
        on_thinking_chunk: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """根据标题与参考卡片生成大纲，返回 {"sections": [{"id", "title", "description"}, ...]}。"""
        refs_block = ""
        for i, c in enumerate(ref_cards[:10], 1):
            refs_block += f"\n[{i}] {c.get('title', '')}\n{c.get('summary', '')[:1200]}\n"
        prompt = self._load_prompt("ai_blog_outline_prompt").format(
            title=title,
            style=style,
            audience=audience,
            refs_block=refs_block or "（无）",
        )
        logger.info("[blog_outline] prompt=\n%s", prompt)
        messages = [{"role": "user", "content": prompt}]
        if on_thinking_chunk:
            raw_parts = []
            thinking_parts = []
            for content_delta, thinking_delta in self.ai_client.chat_full_stream(messages):
                if content_delta:
                    raw_parts.append(content_delta)
                if thinking_delta and on_thinking_chunk:
                    thinking_parts.append(thinking_delta)
                    on_thinking_chunk(thinking_delta)
            raw = "".join(raw_parts)
            if on_thinking and thinking_parts:
                on_thinking("".join(thinking_parts))
        else:
            result = self.ai_client.chat_full(messages)
            raw = result["content"]
            if on_thinking and result.get("thinking"):
                on_thinking(result["thinking"])
        logger.info("[blog_outline] raw_len=%d raw_preview=%s", len(raw), raw[:300] if raw else "")
        outline = _parse_outline_json(raw)
        logger.info("[blog_outline] parsed sections=%s", outline.get("sections", []))
        return outline

    def synthesize_refs(self, ref_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为 ref_cards 生成 key_points，返回增强后的 ref_cards。"""
        if not ref_cards:
            return []
        refs_block = ""
        for i, c in enumerate(ref_cards[:15], 1):
            rid = c.get("ref_id") or f"r{i}"
            refs_block += f"\n[{i}] ref_id={rid}\n标题: {c.get('title', '')}\n{c.get('summary', '')[:2000]}\n"
        prompt = self._load_prompt("ai_synthesize_refs_prompt").format(refs_block=refs_block.strip() or "（无）")
        messages = [{"role": "user", "content": prompt}]
        raw = self.ai_client.chat(messages)
        out = _parse_synthesize_refs_json(raw, ref_cards)
        logger.info("[synthesize_refs] in=%d out=%d", len(ref_cards), len(out))
        return out

    def plan_article(
        self,
        title: str,
        ref_cards: List[Dict[str, Any]],
        outline: Dict[str, Any],
        style: str = "专业报告",
        audience: str = "技术从业者",
    ) -> Dict[str, Any]:
        """根据标题、ref_cards、outline 生成写作蓝图。"""
        outline_block = ""
        for s in (outline.get("sections") or []):
            outline_block += f"- {s.get('id', '')} {s.get('title', '')}: {s.get('description', '')}\n"
        refs_block = ""
        for c in ref_cards[:15]:
            rid = c.get("ref_id", "")
            refs_block += f"\n[{rid}] {c.get('title', '')}\n"
            for kp in c.get("key_points") or []:
                refs_block += f"  - {kp.get('kp_id', '')}: {kp.get('text', '')}\n"
        prompt = self._load_prompt("ai_plan_article_prompt").format(
            title=title,
            style=style,
            audience=audience,
            outline_block=outline_block.strip() or "（无）",
            refs_block=refs_block.strip() or "（无）",
        )
        messages = [{"role": "user", "content": prompt}]
        raw = self.ai_client.chat(messages)
        return _parse_plan_article_json(raw)

    def generate_blog_section(
        self,
        section_title: str,
        section_goal: str,
        bullet_points: List[str],
        recommended_refs: List[str],
        target_length: int,
        ref_cards: List[Dict[str, Any]],
        style: str = "专业报告",
        audience: str = "技术从业者",
        article_title: str = "",
        on_thinking: Optional[Callable[[str], None]] = None,
        on_thinking_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Plan 驱动：生成单节 Markdown，覆盖 bullet_points，引用 recommended_refs。"""
        kp_to_ref: Dict[str, Dict] = {}
        for c in ref_cards:
            rid = c.get("ref_id", "")
            url = c.get("url", "")
            title_ref = c.get("title", "")
            for kp in c.get("key_points") or []:
                kpid = kp.get("kp_id", "")
                if kpid:
                    kp_to_ref[kpid] = {"text": kp.get("text", ""), "url": url, "title": title_ref}
        recommended_refs_block = ""
        for kpid in (recommended_refs or [])[:10]:
            r = kp_to_ref.get(kpid, {})
            recommended_refs_block += f"\n- {kpid}: {r.get('text', '')} → 引用格式 [《{r.get('title', '')}》]({r.get('url', '')})\n"
        bullet_points_block = "\n".join(f"- {b}" for b in (bullet_points or []))
        refs_block = ""
        for c in ref_cards[:10]:
            refs_block += f"\n- {c.get('title', '')} {c.get('url', '')}\n  {c.get('summary', '')[:500]}\n"
        prompt = self._load_prompt("ai_blog_section_prompt").format(
            article_title=article_title or "（未指定）",
            section_title=section_title,
            section_goal=section_goal,
            bullet_points_block=bullet_points_block or "（无）",
            recommended_refs_block=recommended_refs_block.strip() or "（无）",
            refs_block=refs_block.strip() or "（无）",
            style=style,
            audience=audience,
            target_length=target_length,
        )
        messages = [{"role": "user", "content": prompt}]
        if on_thinking_chunk:
            content_parts = []
            thinking_parts = []
            for content_delta, thinking_delta in self.ai_client.chat_full_stream(messages):
                if content_delta:
                    content_parts.append(content_delta)
                if thinking_delta and on_thinking_chunk:
                    thinking_parts.append(thinking_delta)
                    on_thinking_chunk(thinking_delta)
            content = "".join(content_parts).strip()
            if on_thinking and thinking_parts:
                on_thinking("".join(thinking_parts))
        else:
            result = self.ai_client.chat_full(messages)
            content = (result["content"] or "").strip()
            if on_thinking and result.get("thinking"):
                on_thinking(result["thinking"])
        logger.info("[blog_section] section_title=%s content_len=%d", section_title[:40], len(content))
        return content


def _parse_synthesize_refs_json(raw: str, fallback_ref_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """解析 synthesize_refs 输出的 JSON 数组，补全 ref_id、key_points。"""
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = []
    if not isinstance(data, list):
        data = []
    out = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        ref_id = item.get("ref_id") or f"r{i+1}"
        card = next((c for c in fallback_ref_cards if c.get("ref_id") == ref_id), fallback_ref_cards[i] if i < len(fallback_ref_cards) else {})
        kps = item.get("key_points") or []
        kps = [kp if isinstance(kp, dict) else {"kp_id": f"{ref_id}.k{j+1}", "text": str(kp)} for j, kp in enumerate(kps)]
        for j, kp in enumerate(kps):
            kp.setdefault("kp_id", f"{ref_id}.k{j+1}")
            kp.setdefault("text", kp.get("text", "")[:80])
        out.append({
            "ref_id": ref_id,
            "url": item.get("url") or card.get("url", ""),
            "title": item.get("title") or card.get("title", ""),
            "summary": item.get("summary") or card.get("summary", ""),
            "key_points": kps,
        })
    if not out and fallback_ref_cards:
        for i, c in enumerate(fallback_ref_cards):
            out.append({**c, "ref_id": c.get("ref_id") or f"r{i+1}", "key_points": c.get("key_points") or []})
    return out


def _parse_plan_article_json(raw: str) -> Dict[str, Any]:
    """解析 plan_article 输出的 JSON。"""
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    thesis = data.get("thesis") or "全文核心论点"
    terminology = data.get("terminology")
    if not isinstance(terminology, dict):
        terminology = {}
    sections_plan = data.get("sections_plan") or []
    if not isinstance(sections_plan, list):
        sections_plan = []
    for i, sec in enumerate(sections_plan):
        if not isinstance(sec, dict):
            sections_plan[i] = {"id": f"s{i+1}", "goal": "", "bullet_points": [], "recommended_refs": [], "target_length": 800}
        else:
            sec.setdefault("id", f"s{i+1}")
            sec.setdefault("goal", "")
            sec.setdefault("bullet_points", [])
            sec.setdefault("recommended_refs", [])
            sec.setdefault("target_length", 800)
    return {"thesis": thesis, "terminology": terminology, "sections_plan": sections_plan}


def _parse_outline_json(raw: str) -> Dict[str, Any]:
    """从 LLM 输出解析 outline JSON，容忍 markdown 代码块；补全 id/title/description。"""
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"sections": [{"id": "s1", "title": "引言", "description": "引入主题"}, {"id": "s2", "title": "正文", "description": "核心内容"}, {"id": "s3", "title": "总结", "description": "总结与展望"}]}
    if not isinstance(data.get("sections"), list):
        data["sections"] = [{"id": "s1", "title": "引言", "description": "引入"}, {"id": "s2", "title": "正文", "description": "核心内容"}]
    for i, sec in enumerate(data["sections"]):
        if not isinstance(sec, dict):
            data["sections"][i] = {"id": f"s{i+1}", "title": "小节", "description": ""}
        else:
            sec.setdefault("id", f"s{i+1}")
            sec.setdefault("title", sec.get("title") or "小节")
            sec.setdefault("description", sec.get("description") or "")
    return data


# 全局单例
_ai_service_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance

