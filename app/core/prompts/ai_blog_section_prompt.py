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
4. 字数目标 {target_length} 字 ±15%。

写作节奏要求（降低 AI 痕迹）：
- 句子长短交替：混用 2-5 字短句与 20+ 字长句，避免均匀长度。
- 段首句式多样：不要每段都以「随着」「根据」「首先」开头。
- 可加入疑问句、感叹、个人判断（如「这值得深思」「但事实上」）。
- 适当使用「但」「不过」「反而」等转折词。
- 禁止每节都用「背景/分析/结论」三段式结构，段落组织可灵活变化。

直接输出该小节的 Markdown（可含 ## 小节标题），不要解释。"""
