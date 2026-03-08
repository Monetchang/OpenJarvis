# coding=utf-8
"""自动风格与受众推断模块"""
import json
import logging
from dataclasses import dataclass
from typing import Optional, Any

logger = logging.getLogger(__name__)

VALID_ARTICLE_TYPES = frozenset([
    "tutorial", "paper_review", "engineering_practice", "architecture",
    "business_analysis", "roundup", "career", "commentary", "general",
])


@dataclass
class StyleAudienceDecision:
    article_type: str
    style_profile: str
    audience_profile: str
    confidence: float
    decision_trace: dict


def _infer_rule_based(title: str) -> StyleAudienceDecision:
    """规则引擎推断，作为 LLM 失败时的兜底"""
    t = (title or "").lower()

    if any(k in t for k in ["入门", "新手", "从零", "指南", "教程", "一步步"]):
        return StyleAudienceDecision(
            "tutorial",
            "步骤型教程：短句、清单、示例驱动",
            "初学者/转岗者",
            0.85,
            {"hit": "tutorial_keywords"},
        )
    if any(k in t for k in ["实战", "踩坑", "避坑", "最佳实践", "优化", "性能"]):
        return StyleAudienceDecision(
            "engineering_practice",
            "工程实践复盘：问题→方案→权衡→结果",
            "工程师/架构师",
            0.85,
            {"hit": "engineering_keywords"},
        )
    if any(k in t for k in ["架构", "设计", "系统", "整体方案", "端到端"]):
        return StyleAudienceDecision(
            "architecture",
            "架构评审风：图景→组件→接口→风险",
            "架构师/技术负责人",
            0.8,
            {"hit": "architecture_keywords"},
        )
    if any(k in t for k in ["论文", "benchmark", "评测", "对比实验", "复现"]):
        return StyleAudienceDecision(
            "paper_review",
            "论文解读风：贡献→方法→实验→局限",
            "研究者/高阶工程师",
            0.8,
            {"hit": "paper_keywords"},
        )
    if any(k in t for k in ["top", "清单", "合集", "盘点", "速览"]):
        return StyleAudienceDecision(
            "roundup",
            "结构化盘点：卡片化、短段落、高信息密度",
            "碎片化阅读用户",
            0.8,
            {"hit": "roundup_keywords"},
        )
    if any(k in t for k in ["面试", "求职", "简历", "刷题", "准备"]):
        return StyleAudienceDecision(
            "career",
            "面试辅导风：考点→示例→陷阱",
            "求职者/学生",
            0.8,
            {"hit": "career_keywords"},
        )
    if any(k in t for k in ["产品", "商业", "市场", "定价", "融资", "生态"]):
        return StyleAudienceDecision(
            "business_analysis",
            "产品/商业分析：机会→风险→建议",
            "产品经理/管理者",
            0.8,
            {"hit": "business_keywords"},
        )
    tech_detail_words = ["入门", "教程", "代码", "实现", "api", "架构", "论文", "benchmark"]
    if any(k in t for k in ["趋势", "观点", "争议", "影响", "未来"]) and not any(w in t for w in tech_detail_words):
        return StyleAudienceDecision(
            "commentary",
            "评论分析风：论点→证据→反例→结论",
            "泛技术读者/产品同学",
            0.7,
            {"hit": "commentary_keywords"},
        )
    return StyleAudienceDecision(
        "general",
        "专业报告",
        "技术从业者",
        0.5,
        {"hit": "default"},
    )


def _infer_llm(ai_client: Any, title: str, refs: Optional[list] = None) -> Optional[StyleAudienceDecision]:
    """LLM 推断，失败返回 None"""
    from app.core.prompts.ai_style_infer_prompt import TEMPLATE

    ref_urls = "\n".join(f"- {r}" for r in (refs or []) if isinstance(r, str) and r.strip())
    if not ref_urls:
        ref_urls = "（无）"
    prompt = TEMPLATE.format(title=title or "文章", ref_urls=ref_urls)

    try:
        raw = ai_client.chat([{"role": "user", "content": prompt}], temperature=0.2)
        if not raw or not raw.strip():
            return None
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        at = (data.get("article_type") or "").strip().lower()
        if at not in VALID_ARTICLE_TYPES:
            logger.warning("[style_infer] LLM 返回无效 article_type=%r", at)
            return None
        sp = (data.get("style_profile") or "专业报告").strip()
        ap = (data.get("audience_profile") or "技术从业者").strip()
        return StyleAudienceDecision(
            article_type=at,
            style_profile=sp or "专业报告",
            audience_profile=ap or "技术从业者",
            confidence=0.9,
            decision_trace={"mode": "llm"},
        )
    except json.JSONDecodeError as e:
        logger.warning("[style_infer] LLM 响应 JSON 解析失败: %s", e)
        return None
    except Exception as e:
        logger.warning("[style_infer] LLM 推断异常: %s", e)
        return None


def infer(
    title: str,
    user_style: Optional[str] = None,
    user_audience: Optional[str] = None,
    refs: Optional[list] = None,
    ai_client: Optional[Any] = None,
) -> StyleAudienceDecision:
    """
    根据标题推断 article_type / style_profile / audience_profile。
    用户显式选择时锁定；否则优先 LLM 推断，失败则规则兜底。
    """
    if user_style and user_style.lower() != "auto" and user_audience and user_audience.lower() != "auto":
        return StyleAudienceDecision(
            article_type="user_locked",
            style_profile=user_style,
            audience_profile=user_audience,
            confidence=1.0,
            decision_trace={"mode": "locked"},
        )

    if ai_client:
        decision = _infer_llm(ai_client, title, refs)
        if decision:
            return decision
        logger.info("[style_infer] LLM 推断失败，回退到规则引擎")

    return _infer_rule_based(title)
