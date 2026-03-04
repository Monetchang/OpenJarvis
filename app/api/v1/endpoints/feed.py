# coding=utf-8
"""
RSS 订阅源管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.feed import RSSFeed
from app.models.config import AppConfig
from app.schemas.feed import FeedCreate, FeedUpdate, FeedResponse, BatchFeedCreate
from app.schemas.common import ResponseModel
from app.services.crawler_service import get_crawler_service, fetch_all_active_feeds
from app.utils.validators import validate_url
import json

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


@router.post("/fetch")
def fetch_feeds_now(
    max_feeds: int = Query(0, description="仅抓前N个源，0=全部"),
    db: Session = Depends(get_db)
):
    """手动触发 RSS 抓取，max_feeds>0 时仅抓前 N 个源（快速测试）"""
    import time
    t0 = time.time()
    logger.info("[fetch API] 请求开始 max_feeds=%s", max_feeds or "all")
    try:
        result = fetch_all_active_feeds(db, max_feeds=max_feeds)
        elapsed = time.time() - t0
        logger.info("[fetch API] 请求完成 耗时=%.1fs, 即将返回 data=%s", elapsed, result)
        return {"code": 0, "message": "抓取完成", "data": result}
    except Exception as e:
        logger.exception("[fetch API] 异常: %s", e)
        raise


@router.get("/list")
def get_feed_list(db: Session = Depends(get_db)):
    """获取订阅源列表"""
    feeds = db.query(RSSFeed).filter(RSSFeed.is_active == 1).all()
    
    # 从数据库读取全局配置
    rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
    
    result = []
    for feed in feeds:
        result.append({
            "id": feed.id,
            "name": feed.name,
            "url": feed.feed_url,
            "pushCount": feed.push_count or 10,
            "isTrusted": bool(feed.is_trusted),
            "createdAt": feed.created_at.isoformat() if feed.created_at else ""
        })
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "feeds": result,
            "schedule": rss_schedule  # 返回全局定时配置
        }
    }


@router.post("/create")
def create_feed(feed_data: FeedCreate, db: Session = Depends(get_db)):
    """添加订阅源"""
    try:
        logger.info(
            f"创建订阅源请求: feed_name={feed_data.name}, url={feed_data.url}, pushCount={feed_data.pushCount}"
        )
        
        # 验证 URL 格式
        if not validate_url(feed_data.url):
            logger.warning(f"URL 格式验证失败: {feed_data.url}")
            raise HTTPException(status_code=400, detail="RSS URL 格式不正确")
        
        # 验证 RSS URL 可访问性
        crawler_service = get_crawler_service()
        if not crawler_service.validate_rss_url(feed_data.url):
            logger.warning(f"RSS URL 无法访问: {feed_data.url}")
            raise HTTPException(status_code=400, detail="无法访问该RSS源")
        
        # 生成 ID
        import uuid
        feed_id = f"feed_{uuid.uuid4().hex[:8]}"
        
        # 检查是否已存在
        existing = db.query(RSSFeed).filter(RSSFeed.feed_url == feed_data.url).first()
        if existing:
            logger.warning(f"订阅源已存在: {feed_data.url}")
            raise HTTPException(status_code=400, detail="该订阅源已存在")
        
        # 从数据库读取全局配置
        rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
        translation_enabled = get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
        
        # 创建记录（使用全局配置，所有源共享定时和翻译设置）
        new_feed = RSSFeed(
            id=feed_id,
            name=feed_data.name,
            feed_url=feed_data.url,
            is_active=1,
            schedule=rss_schedule,
            push_count=feed_data.pushCount,
            enable_translation=1 if translation_enabled else 0,
            is_trusted=1 if feed_data.isTrusted else 0,
        )
        
        db.add(new_feed)
        db.commit()
        db.refresh(new_feed)
        logger.info(f"订阅源创建成功: id={new_feed.id}, name={new_feed.name}")
        if getattr(feed_data, "fetchNow", False):
            fetch_all_active_feeds(db)
        return {
            "code": 0,
            "message": "添加成功",
            "data": {
                "id": new_feed.id,
                "name": new_feed.name,
                "url": new_feed.feed_url,
                "pushCount": new_feed.push_count,
                "isTrusted": bool(new_feed.is_trusted),
                "createdAt": new_feed.created_at.isoformat() if new_feed.created_at else ""
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建订阅源失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建订阅源失败: {str(e)}")


@router.post("/batch-create")
def batch_create_feeds(body: BatchFeedCreate, db: Session = Depends(get_db)):
    """批量添加订阅源，支持 JSON 列表"""
    import uuid
    crawler_service = get_crawler_service()
    rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
    translation_enabled = get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
    created = []
    skipped = []
    failed = []
    for item in body.feeds:
        try:
            if not validate_url(item.url):
                failed.append({"name": item.name, "url": item.url, "reason": "RSS URL 格式不正确"})
                continue
            if not crawler_service.validate_rss_url(item.url):
                failed.append({"name": item.name, "url": item.url, "reason": "无法访问该RSS源"})
                continue
            existing = db.query(RSSFeed).filter(RSSFeed.feed_url == item.url).first()
            if existing:
                skipped.append({"name": item.name, "url": item.url})
                continue
            feed_id = f"feed_{uuid.uuid4().hex[:8]}"
            new_feed = RSSFeed(
                id=feed_id,
                name=item.name,
                feed_url=item.url,
                is_active=1,
                schedule=rss_schedule,
                push_count=item.pushCount,
                enable_translation=1 if translation_enabled else 0,
                is_trusted=1 if item.isTrusted else 0,
            )
            db.add(new_feed)
            db.commit()
            db.refresh(new_feed)
            created.append({
                "id": new_feed.id,
                "name": new_feed.name,
                "url": new_feed.feed_url,
                "pushCount": new_feed.push_count,
                "isTrusted": bool(new_feed.is_trusted),
                "createdAt": new_feed.created_at.isoformat() if new_feed.created_at else ""
            })
        except Exception as e:
            db.rollback()
            failed.append({"name": item.name, "url": item.url, "reason": str(e)})
    if body.fetchNow and created:
        fetch_all_active_feeds(db)
    return {
        "code": 0,
        "message": "批量添加完成",
        "data": {"created": created, "skipped": skipped, "failed": failed}
    }


@router.put("/update/{feedId}")
def update_feed(feedId: str, feed_data: FeedUpdate, db: Session = Depends(get_db)):
    """修改订阅源"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feedId).first()
    
    if not feed:
        raise HTTPException(status_code=404, detail="订阅源不存在")
    
    # 从数据库读取全局配置
    rss_schedule = get_config_value(db, "rss_schedule", settings.RSS_SCHEDULE)
    translation_enabled = get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
    
    # 更新字段（schedule 和 enableTranslation 不再允许单独修改，所有源共享全局配置）
    if feed_data.name is not None:
        feed.name = feed_data.name
    if feed_data.url is not None:
        feed.feed_url = feed_data.url
    if feed_data.pushCount is not None:
        feed.push_count = feed_data.pushCount
    if feed_data.isTrusted is not None:
        feed.is_trusted = 1 if feed_data.isTrusted else 0
    feed.schedule = rss_schedule
    feed.enable_translation = 1 if translation_enabled else 0
    db.commit()
    db.refresh(feed)
    if getattr(feed_data, "fetchNow", False):
        fetch_all_active_feeds(db)
    return {
        "code": 0,
        "message": "更新成功",
        "data": {
            "id": feed.id,
            "name": feed.name,
            "url": feed.feed_url,
            "pushCount": feed.push_count,
            "isTrusted": bool(feed.is_trusted),
            "createdAt": feed.created_at.isoformat() if feed.created_at else ""
        }
    }


@router.delete("/delete/{feedId}")
def delete_feed(feedId: str, db: Session = Depends(get_db)):
    """删除订阅源"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feedId).first()
    
    if not feed:
        raise HTTPException(status_code=404, detail="订阅源不存在")
    
    # 软删除
    feed.is_active = 0
    db.commit()
    
    return {
        "code": 0,
        "message": "删除成功",
        "data": {"success": True}
    }


@router.put("/trust/{feedId}")
def toggle_trust(feedId: str, db: Session = Depends(get_db)):
    """切换订阅源信任状态"""
    feed = db.query(RSSFeed).filter(RSSFeed.id == feedId).first()
    if not feed:
        raise HTTPException(status_code=404, detail="订阅源不存在")
    feed.is_trusted = 0 if feed.is_trusted else 1
    db.commit()
    return {
        "code": 0,
        "message": "已设为信任源" if feed.is_trusted else "已取消信任源",
        "data": {"id": feed.id, "isTrusted": bool(feed.is_trusted)}
    }

