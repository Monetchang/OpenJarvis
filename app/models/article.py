# coding=utf-8
"""
文章推送数据模型
"""
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class RSSItem(Base):
    """RSS 文章条目表（复用 rss_items）"""
    __tablename__ = "rss_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    title_zh = Column(Text)  # 翻译后的中文标题，仅标题翻译时使用
    feed_id = Column(String, ForeignKey("rss_feeds.id"), nullable=False)
    url = Column(Text, nullable=False)
    guid = Column(String(512))
    published_at = Column(String)
    summary = Column(Text)
    author = Column(String)
    first_crawl_time = Column(String, nullable=False)
    last_crawl_time = Column(String, nullable=False)
    crawl_count = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # 扩展字段
    is_read = Column(Boolean, default=False)  # 标记已读
    domain_id = Column(Integer, ForeignKey("article_domains.id", ondelete="SET NULL"))
    matched_keywords = Column(JSON)  # 匹配的关键词信息
    interpret_result = Column(JSON)  # AI 解读结果，结构化 JSON

