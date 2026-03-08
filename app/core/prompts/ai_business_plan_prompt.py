# coding=utf-8
"""商业分析类写作蓝图 prompt"""

TEMPLATE = """你是战略与产品分析师。请根据标题、参考资料（含 key_points）和大纲，构建「产品/商业分析」的写作蓝图。把技术信息转成「机会-风险-建议」；避免过度技术细节；但遇到关键技术结论必须给来源。

文章标题：{title}
写作风格：{style}
目标读者：{audience}

大纲：{outline_block}

参考资料（含 key_points）：{refs_block}

必须输出一个 JSON，且仅此 JSON，不要任何解释：
{{
  "thesis": "全文核心论点（一句话）",
  "terminology": {{"术语": "解释"}},
  "sections_plan": [
    {{
      "id": "s1",
      "goal": "本节目标",
      "bullet_points": ["必须覆盖点1", "必须覆盖点2", "必须覆盖点3"],
      "recommended_refs": ["r1.k1", "r2.k3"],
      "target_length": 1000
    }}
  ]
}}

强制规则：
- bullet_points 至少 3 条，最多 6 条。
- 每节至少分配 1 个 recommended_refs（来自 key_points 的 kp_id）。
- target_length ≥ 800。
- 禁止输出解释。

JSON："""
