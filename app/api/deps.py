# coding=utf-8
"""
依赖注入
"""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

# 数据库会话依赖
def get_db_session() -> Session:
    """获取数据库会话"""
    return Depends(get_db)

