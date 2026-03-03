# coding=utf-8
"""
全局配置管理路由
"""
import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.config import AppConfig
from app.models.feed import RSSFeed
from app.schemas.config import ConfigResponse, ConfigUpdateRequest
from app.schemas.common import ResponseModel
from app.services import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter()


def get_config_value(db: Session, key: str, default_value):
    """获取配置值，如果不存在则返回默认值"""
    config = db.query(AppConfig).filter(AppConfig.key == key).first()
    if config:
        try:
            return json.loads(config.value)
        except:
            return config.value
    return default_value


def set_config_value(db: Session, key: str, value):
    """设置配置值"""
    config = db.query(AppConfig).filter(AppConfig.key == key).first()
    if config:
        config.value = json.dumps(value) if not isinstance(value, str) else value
    else:
        config = AppConfig(
            key=key,
            value=json.dumps(value) if not isinstance(value, str) else value
        )
        db.add(config)
    db.commit()


@router.get("/global")
def get_global_config(db: Session = Depends(get_db)):
    """获取全局配置"""
    try:
        # 从数据库读取，如果不存在则使用 settings 默认值
        rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
        translation_enabled = get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
        
        logger.info(f"获取全局配置: rss_schedule={rss_schedule}, translation_enabled={translation_enabled}")
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "rssSchedule": rss_schedule,
                "translationEnabled": translation_enabled
            }
        }
    except Exception as e:
        logger.error(f"获取全局配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/global")
def update_global_config(config_data: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """更新全局配置"""
    try:
        logger.info(
            f"更新全局配置请求",
            extra={
                "rssSchedule": config_data.rssSchedule,
                "translationEnabled": config_data.translationEnabled,
            }
        )
        
        # 更新 RSS 定时
        if config_data.rssSchedule is not None:
            set_config_value(db, "rss_schedule", config_data.rssSchedule)
            # 同步更新所有 RSS 源的定时配置
            db.query(RSSFeed).filter(RSSFeed.is_active == 1).update({
                RSSFeed.schedule: config_data.rssSchedule
            })
            scheduler_service.reschedule(config_data.rssSchedule)
            logger.info(f"更新 RSS 定时配置: {config_data.rssSchedule}")
        
        # 更新翻译开关
        if config_data.translationEnabled is not None:
            set_config_value(db, "translation_enabled", config_data.translationEnabled)
            # 同步更新所有 RSS 源的翻译配置
            db.query(RSSFeed).filter(RSSFeed.is_active == 1).update({
                RSSFeed.enable_translation: 1 if config_data.translationEnabled else 0
            })
            logger.info(f"更新翻译配置: {config_data.translationEnabled}")
        
        # 读取最新配置
        rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
        translation_enabled = get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
        
        return {
            "code": 0,
            "message": "更新成功",
            "data": {
                "rssSchedule": rss_schedule,
                "translationEnabled": translation_enabled
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新全局配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

