# coding=utf-8
"""论文解读类小节生成 prompt"""

TEMPLATE = """你是严谨的技术研究编辑。请只写以下这一小节，不要写其他小节。你必须只基于「参考资料摘要/要点」写作；无法从资料推导的内容，必须明确标注「资料未覆盖/需进一步验证」。禁止编造实验数据、组织、年份、指标。

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
4. 结构：问题-假设-方法-实现要点；遇到术语必须在首次出现时解释。
5. 字数目标 {target_length} 字 ±15%。

直接输出该小节的 Markdown（可含 ## 小节标题），不要解释。"""
