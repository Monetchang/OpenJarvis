# coding=utf-8
"""文章生成 prompt"""

TEMPLATE = """你是一位专业的内容创作者。请根据以下要求撰写一篇文章：

选题：{title}
{refs_text}
写作风格：{style}
目标人群：{audience}
文章长度：{length_desc}
输出语言：{language_desc}

要求：
1. 使用 Markdown 格式
2. 包含标题、引言、正文（多个小节）、总结
3. 内容专业、有深度、易读，可引用参考资料
4. 适合目标人群阅读

请直接输出 Markdown 格式的完整文章："""
