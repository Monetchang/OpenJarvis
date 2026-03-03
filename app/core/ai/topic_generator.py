# coding=utf-8
"""
AI 博客选题生成器模块

基于推送的新闻内容智能生成 AI 技术相关博客选题建议
每个选题关联相关的文档链接，方便深入研究
"""

import importlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .client import AIClient
from app.models.ai import BlogTopic

logger = logging.getLogger(__name__)


@dataclass
class BlogTopicsResult:
    """博客选题生成结果"""
    topics: List[BlogTopic] = field(default_factory=list)
    success: bool = False
    error: str = ""
    news_count: int = 0                       # 参与分析的新闻数量


class BlogTopicsGenerator:
    """AI 博客选题生成器"""

    def __init__(self, topics_config: Dict[str, Any], ai_config: Dict[str, Any]):
        """
        初始化博客选题生成器

        Args:
            topics_config: AI 博客选题配置 (AI_BLOG_TOPICS)
            ai_config: AI 模型配置（LiteLLM 格式）
        """
        self.topics_config = topics_config
        self.ai_config = ai_config

        # 选题配置
        self.enabled = topics_config.get("ENABLED", False)
        self.min_topics = topics_config.get("MIN_TOPICS", 3)
        self.max_topics = topics_config.get("MAX_TOPICS", 5)
        self.include_platforms = topics_config.get("INCLUDE_PLATFORMS", True)
        self.include_rss = topics_config.get("INCLUDE_RSS", True)
        self.max_news_for_generation = topics_config.get("MAX_NEWS_FOR_GENERATION", 100)
        self.focus_areas = topics_config.get("FOCUS_AREAS", [])
        self.language = topics_config.get("LANGUAGE", "Chinese")
        self.prompt_module = topics_config.get("PROMPT_MODULE", "ai_blog_topics_prompt")

        # AI 客户端
        self.ai_client = AIClient(ai_config) if self.enabled else None

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """从 app.core.prompts 加载提示词模块"""
        try:
            mod = importlib.import_module(f"app.core.prompts.{self.prompt_module}")
            return getattr(mod, "TEMPLATE", "") or self._get_default_prompt()
        except Exception as e:
            logger.warning("加载博客选题提示词失败: %s", e)
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return """你是一位资深的 AI 技术博客作者和内容策划专家。

任务：基于以下新闻的标题和摘要，生成 {min_topics} 到 {max_topics} 个高质量的 AI 技术博客选题建议。请充分结合摘要中的关键信息进行分析和归纳。

输出要求：
1. 每个选题必须：
   - 有吸引力且专业的标题
   - 简洁的选题描述（50-150字）
   - 列出3-5个相关的新闻链接作为参考资料

2. 选题特点：
   - 聚焦当前 AI 技术热点和趋势
   - 有深度、有洞察力，避免泛泛而谈
   - 适合深入研究和撰写技术博客
   - 结合多个相关新闻，找出共同趋势或对比点

3. 严格的 JSON 格式输出：
{{
  "topics": [
    {{
      "title": "选题标题",
      "description": "选题描述，说明为什么这个话题值得关注",
      "related_articles": [
        {{
          "title": "文章标题1",
          "url": "https://..."
        }},
        {{
          "title": "文章标题2",
          "url": "https://..."
        }}
      ]
    }}
  ]
}}

新闻内容：
{news_content}

请直接输出 JSON，不要添加任何其他文字。
"""

    def _collect_news(self, platforms_news: List[Dict], rss_items: Dict, standalone_data: Dict = None) -> List[Dict[str, str]]:
        """
        从推送数据中收集所有新闻

        Args:
            platforms_news: 平台新闻列表
            rss_items: RSS 统计数据（关键词分组格式）
            standalone_data: 独立展示区数据

        Returns:
            新闻列表: [{"title": "...", "url": "...", "source": "...", "summary": "..."}, ...]
        """
        news_list = []
        seen_urls = set()

        def _item(title, url, source, summary=""):
            return {"title": title, "url": url, "source": source, "summary": summary or ""}

        # 收集平台新闻
        if self.include_platforms and platforms_news:
            for item in platforms_news:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    news_list.append(_item(
                        item.get("title", ""), url, item.get("platform", "未知平台"),
                        item.get("summary") or item.get("abstract", "")
                    ))
                    seen_urls.add(url)

        # 收集 RSS 新闻
        if self.include_rss and rss_items:
            for key, data in rss_items.items():
                if not isinstance(data, dict):
                    continue
                if "titles" in data:
                    # 关键词分组格式：{keyword: {"titles": [...]}}
                    for title_item in data["titles"]:
                        if isinstance(title_item, dict):
                            url = title_item.get("url", "")
                            if url and url not in seen_urls:
                                news_list.append(_item(
                                    title_item.get("title", ""), url, title_item.get("feed_name", "RSS"),
                                    title_item.get("summary", "")
                                ))
                                seen_urls.add(url)
                else:
                    # API 扁平格式：{0: {title, url, feed_id, summary, ...}, 1: {...}}
                    url = data.get("url", "")
                    if url and url not in seen_urls:
                        news_list.append(_item(
                            data.get("title", ""), url, data.get("feed_id", "RSS"),
                            data.get("summary", "")
                        ))
                        seen_urls.add(url)

        # 收集独立展示区的 RSS 新闻（如果有）
        if self.include_rss and standalone_data and "rss" in standalone_data:
            for feed_id, feed_data in standalone_data["rss"].items():
                if isinstance(feed_data, dict) and "items" in feed_data:
                    for item in feed_data["items"]:
                        url = item.get("url", "")
                        if url and url not in seen_urls:
                            news_list.append(_item(
                                item.get("title", ""), url, item.get("feed_name", "RSS"),
                                item.get("summary", "")
                            ))
                            seen_urls.add(url)

        # 限制新闻数量
        if self.max_news_for_generation > 0 and len(news_list) > self.max_news_for_generation:
            news_list = news_list[:self.max_news_for_generation]

        return news_list

    def _build_prompt(self, news_list: List[Dict[str, str]]) -> str:
        """
        构建提示词

        Args:
            news_list: 新闻列表

        Returns:
            完整提示词
        """
        # 格式化新闻内容（标题 + 摘要 + 链接）
        news_content = ""
        for idx, news in enumerate(news_list, 1):
            parts = [f"{idx}. [{news['source']}] {news['title']}"]
            if news.get("summary", "").strip():
                parts.append(f"   摘要: {news['summary'].strip()}")
            parts.append(f"   链接: {news['url']}")
            news_content += "\n".join(parts) + "\n\n"

        # 格式化关注领域
        focus_areas_str = ""
        if self.focus_areas:
            focus_areas_str = "\n".join(f"- {area}" for area in self.focus_areas)
        else:
            focus_areas_str = "不限制（但应聚焦 AI 技术相关话题）"

        # 填充模板
        prompt = self.prompt_template.format(
            min_topics=self.min_topics,
            max_topics=self.max_topics,
            focus_areas=focus_areas_str,
            news_content=news_content.strip()
        )

        return prompt

    def _parse_response(self, response: str) -> List[BlogTopic]:
        """
        解析 AI 响应

        Args:
            response: AI 响应文本

        Returns:
            博客选题列表
        """
        try:
            # 清理响应（移除可能的 markdown 代码块标记）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # 解析 JSON
            data = json.loads(response)
            
            if not isinstance(data, dict) or "topics" not in data:
                logger.warning("AI 响应格式错误: 缺少 'topics' 字段")
                return []

            topics = []
            for topic_data in data["topics"]:
                if not isinstance(topic_data, dict):
                    continue

                topic = BlogTopic(
                    title=topic_data.get("title", ""),
                    description=topic_data.get("description", ""),
                )
                # 解析关联文章（AI 返回的 related_articles）
                raw = topic_data.get("related_articles")
                if isinstance(raw, list):
                    topic.related_articles = [
                        {"title": x.get("title", ""), "url": x.get("url", ""), "source": x.get("source", "参考文章")}
                        for x in raw if isinstance(x, dict) and (x.get("title") or x.get("url"))
                    ]
                else:
                    topic.related_articles = []

                if topic.title and topic.description:
                    topics.append(topic)

            return topics

        except json.JSONDecodeError as e:
            logger.error("解析 AI 响应 JSON 失败: %s, 响应: %s", e, response[:500])
            return []
        except Exception as e:
            logger.error("解析 AI 响应失败: %s", e)
            return []

    def generate(self, platforms_news: List[Dict] = None, rss_items: Dict = None, standalone_data: Dict = None) -> BlogTopicsResult:
        """
        生成博客选题

        Args:
            platforms_news: 平台新闻列表
            rss_items: RSS 统计数据
            standalone_data: 独立展示区数据

        Returns:
            博客选题生成结果
        """
        result = BlogTopicsResult()

        if not self.enabled:
            result.error = "博客选题生成未启用"
            return result

        if not self.ai_client:
            result.error = "AI 客户端未初始化"
            return result

        try:
            # 收集新闻
            news_list = self._collect_news(
                platforms_news=platforms_news or [],
                rss_items=rss_items or {},
                standalone_data=standalone_data
            )

            result.news_count = len(news_list)

            if not news_list:
                result.error = "没有可用的新闻内容"
                return result

            if result.news_count < 3:
                result.error = f"新闻数量不足（至少需要 3 条，当前仅 {result.news_count} 条）"
                return result

            logger.info("博客选题: 基于 %d 条新闻生成选题", result.news_count)

            # 构建提示词
            prompt = self._build_prompt(news_list)

            # 调用 AI（使用消息列表格式）
            messages = [
                {"role": "user", "content": prompt}
            ]
            response = self.ai_client.chat(messages)

            if not response:
                result.error = "AI 未返回响应"
                return result

            # 解析响应
            topics = self._parse_response(response)

            if not topics:
                result.error = "未能解析出有效的选题"
                return result

            # 验证选题数量
            if len(topics) < self.min_topics:
                logger.warning("生成的选题数量 (%d) 少于最小要求 (%d)", len(topics), self.min_topics)

            result.topics = topics
            result.success = True
            logger.info("博客选题: 成功生成 %d 个选题", len(topics))

            return result

        except Exception as e:
            result.error = f"生成博客选题时出错: {e}"
            logger.exception("博客选题生成失败: %s", result.error)
            return result

