# coding=utf-8
"""博客大纲生成 prompt"""

TEMPLATE = """你是一位专业的内容策划。根据以下文章标题和参考资料，生成一篇博客的大纲。

文章标题：{title}
写作风格：{style}
目标读者：{audience}
参考资料：{refs_block}

要求：
1. 输出 3-5 个小节，每节有 id、title、description。
2. id 格式为 s1、s2、s3...；title 为中文小节标题；description 为一句话描述该节要写什么。
3. 每节必须有明确问题意识，description 不得泛泛而谈。
4. 不得出现「首先、其次、最后」式模板语言。
5. 只输出一个 JSON 对象，不要其他说明。格式：{{"sections": [{{"id": "s1", "title": "引言", "description": "简要引入主题与背景"}}, ...]}}

JSON："""
