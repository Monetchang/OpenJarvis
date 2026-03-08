# coding=utf-8
"""论文解读类写作蓝图 prompt"""

TEMPLATE = """你是严谨的技术研究编辑。请根据标题、参考资料（含 key_points）和大纲，构建「论文解读」的写作蓝图。必须只基于「参考资料摘要/要点」；无法从资料推导的内容，必须明确标注「资料未覆盖/需进一步验证」。禁止编造实验数据、组织、年份、指标。

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
