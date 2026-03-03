# coding=utf-8
"""博客小节生成 prompt（plan 驱动）"""

TEMPLATE = """你是专业的内容创作者。请只写以下这一小节，不要写其他小节。

文章标题：{article_title}

本节标题：{section_title}
本节目标：{section_goal}

必须覆盖的要点（bullet_points）：
{bullet_points_block}

推荐引用（至少引用 1-2 条，格式 [来源标题](URL)）：
{recommended_refs_block}

参考资料（含 URL，用于正确标注引用来源）：
{refs_block}

写作风格：{style}；目标读者：{audience}。

必须遵守：
1. 覆盖所有 bullet_points。
2. 至少引用 1-2 条 recommended_refs，引用格式：[来源标题](URL)。
3. 禁止编造数据。
4. 结构：背景 → 分析 → 论证 → 小结。
5. 字数目标 {target_length} 字 ±15%。

直接输出该小节的 Markdown（可含 ## 小节标题），不要解释。"""
