# coding=utf-8
"""
AI 选题数据模型
"""
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class BlogTopic(Base):
    """AI 博客选题表（复用 blog_topics）"""
    __tablename__ = "blog_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    generated_at = Column(TIMESTAMP, server_default=func.now())
    date = Column(String, nullable=False)
    crawl_time = Column(String, nullable=False)
    news_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())


class TopicReference(Base):
    """选题参考资料表（复用 topic_references）"""
    __tablename__ = "topic_references"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("blog_topics.id", ondelete="CASCADE"), nullable=False)
    article_title = Column(Text, nullable=False)
    article_url = Column(Text, nullable=False)
    source = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())

