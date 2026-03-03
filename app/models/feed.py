# coding=utf-8
"""
RSS 订阅源数据模型
"""
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class RSSFeed(Base):
    """RSS 订阅源表（复用 rss_feeds）"""
    __tablename__ = "rss_feeds"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    feed_url = Column(String, default="")
    is_active = Column(Integer, default=1)
    last_fetch_time = Column(String)
    last_fetch_status = Column(String)
    item_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # 扩展字段（存储为 JSON 字符串或单独字段）
    schedule = Column(String, default="0 9 * * *")  # cron 表达式
    push_count = Column(Integer, default=10)  # 推送数量
    enable_translation = Column(Integer, default=0)  # 是否启用翻译
    is_trusted = Column(Integer, default=0)  # 是否信任源（跳过分类匹配，直接保留）

