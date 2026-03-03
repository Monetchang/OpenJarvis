# coding=utf-8
"""
邮件订阅者模型
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
