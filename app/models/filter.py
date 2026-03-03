# coding=utf-8
"""
文章过滤数据模型
"""
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class ArticleDomain(Base):
    """关键领域表"""
    __tablename__ = "article_domains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    max_results = Column(Integer, default=3)  # 该领域最多展示条数
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class ArticleKeyword(Base):
    """关键词规则表"""
    __tablename__ = "article_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("article_domains.id", ondelete="CASCADE"), nullable=False)
    keyword_type = Column(String(20), nullable=False, default="positive")  # positive/negative
    keyword_text = Column(Text, nullable=False)
    is_regex = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)  # 必须词 (+)
    alias = Column(String(255))
    priority = Column(Integer, default=0)
    max_results = Column(Integer)  # 限制数量 (@N)
    created_at = Column(TIMESTAMP, server_default=func.now())

