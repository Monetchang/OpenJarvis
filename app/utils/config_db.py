# coding=utf-8
"""数据库配置读取"""
import json
from sqlalchemy.orm import Session
from app.models.config import AppConfig


def get_config_value(db: Session, key: str, default):
    config = db.query(AppConfig).filter(AppConfig.key == key).first()
    if config:
        try:
            return json.loads(config.value)
        except Exception:
            return config.value
    return default
