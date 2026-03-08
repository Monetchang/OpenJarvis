# coding=utf-8
"""Prompt Pack 注册表：按 article_type 选择不同 prompt 模板与参数"""

PROMPT_PACKS = {
    "tutorial_beginner": {
        "outline": "ai_tutorial_outline_prompt",
        "plan": "ai_tutorial_plan_prompt",
        "section": "ai_tutorial_section_prompt",
        "params": {"temperature_outline": 0.4, "temperature_plan": 0.3, "temperature_section": 0.7},
    },
    "paper_review_pro": {
        "outline": "ai_paper_review_outline_prompt",
        "plan": "ai_paper_review_plan_prompt",
        "section": "ai_paper_review_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.6},
    },
    "business_analysis": {
        "outline": "ai_business_outline_prompt",
        "plan": "ai_business_plan_prompt",
        "section": "ai_business_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.6},
    },
    "engineering_practice": {
        "outline": "ai_blog_outline_prompt",
        "plan": "ai_plan_article_prompt",
        "section": "ai_blog_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.7},
    },
    "architecture": {
        "outline": "ai_blog_outline_prompt",
        "plan": "ai_plan_article_prompt",
        "section": "ai_blog_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.7},
    },
    "general": {
        "outline": "ai_blog_outline_prompt",
        "plan": "ai_plan_article_prompt",
        "section": "ai_blog_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.7},
    },
    "user_locked": {
        "outline": "ai_blog_outline_prompt",
        "plan": "ai_plan_article_prompt",
        "section": "ai_blog_section_prompt",
        "params": {"temperature_outline": 0.3, "temperature_plan": 0.3, "temperature_section": 0.7},
    },
}


ARTICLE_TYPE_TO_PACK = {
    "tutorial": "tutorial_beginner",
    "paper_review": "paper_review_pro",
    "business_analysis": "business_analysis",
    "engineering_practice": "engineering_practice",
    "architecture": "architecture",
    "roundup": "general",
    "career": "general",
    "commentary": "general",
    "general": "general",
    "user_locked": "user_locked",
}


def get_pack_for_article_type(article_type: str) -> dict:
    """根据 article_type 获取 prompt pack，未知类型返回 general"""
    pack_id = ARTICLE_TYPE_TO_PACK.get(article_type, "general")
    return PROMPT_PACKS.get(pack_id, PROMPT_PACKS["general"])
