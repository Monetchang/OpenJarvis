# coding=utf-8
"""
订阅者模型：邮件、飞书
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class EmailSubscriber(Base):
    """邮件订阅者表"""
    __tablename__ = "email_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    is_active = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())


class FeishuSubscriber(Base):
    """飞书 Webhook 订阅者表"""
    __tablename__ = "feishu_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    webhook_url = Column(String(512), nullable=False, unique=True)
    is_active = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
