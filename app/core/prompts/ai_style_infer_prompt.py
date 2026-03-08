# coding=utf-8
"""AI 风格/受众推断 prompt"""

TEMPLATE = """根据文章标题和参考链接，推断文章类型、写作风格、目标受众。

标题：{title}
参考链接（可选）：
{ref_urls}

可选类型及对应风格/受众（必须严格选择其一）：
- tutorial: 步骤型教程：短句、清单、示例驱动 | 初学者/转岗者
- paper_review: 论文解读风：贡献→方法→实验→局限 | 研究者/高阶工程师
- engineering_practice: 工程实践复盘：问题→方案→权衡→结果 | 工程师/架构师
- architecture: 架构评审风：图景→组件→接口→风险 | 架构师/技术负责人
- business_analysis: 产品/商业分析：机会→风险→建议 | 产品经理/管理者
- roundup: 结构化盘点：卡片化、短段落、高信息密度 | 碎片化阅读用户
- career: 面试辅导风：考点→示例→陷阱 | 求职者/学生
- commentary: 评论分析风：论点→证据→反例→结论 | 泛技术读者/产品同学
- general: 专业报告 | 技术从业者

输出 JSON，不要其他文字：
{{"article_type": "类型英文名", "style_profile": "风格描述", "audience_profile": "受众描述"}}
"""
