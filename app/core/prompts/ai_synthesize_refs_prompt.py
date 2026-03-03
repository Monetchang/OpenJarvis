# coding=utf-8
"""参考资料合成 prompt：为每张 ref_card 生成 key_points"""

TEMPLATE = """你是一位严谨的资料整理员。请根据以下每条参考资料的 title 和 summary，提炼 3-6 条关键要点（key_points）。

约束：
1. 每条 key_point 不超过 80 字。
2. 严禁编造未出现在原文 summary 中的事实。
3. 只输出一个 JSON 数组，每项格式：{{"ref_id": "r1", "url": "...", "title": "...", "summary": "...", "key_points": [{{"kp_id": "r1.k1", "text": "要点内容"}}, ...]}}
4. ref_id 必须与输入的序号对应（r1、r2、r3...）。

输入参考资料：
{refs_block}

JSON："""
