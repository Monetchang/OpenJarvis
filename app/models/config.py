# coding=utf-8
"""
应用配置数据模型
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class AppConfig(Base):
    """应用全局配置表"""
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)  # 配置键
    value = Column(String, nullable=False)  # 配置值（JSON 字符串）
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

