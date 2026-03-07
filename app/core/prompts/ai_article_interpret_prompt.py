# coding=utf-8
"""文章解读 prompt"""

TEMPLATE = """你是一名 AI 研究分析师，请对以下 AI 相关文章进行深度解读。

要求：
- 不要编造信息
- 保留关键技术细节
- 语言专业但易读
- 输出 JSON

文章标题：
{title}

来源：
{source}

文章内容：
{content}

请输出：

{{
  "summary": "150字以内摘要",
  "key_points": [
    "核心观点1",
    "核心观点2",
    "核心观点3"
  ],
  "technical_points": [
    "关键技术点1",
    "关键技术点2"
  ],
  "important_facts": [
    "重要事实或数据1",
    "重要事实或数据2"
  ],
  "industry_impact": "这篇文章对AI行业的意义",
  "tags": ["LLM", "Agent", "AI Infra"]
}}"""
