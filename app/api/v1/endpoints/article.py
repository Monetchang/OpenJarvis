# coding=utf-8
"""
文章推送路由
"""
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func, cast, Date

from app.core.database import get_db
from app.models.article import RSSItem
from app.models.feed import RSSFeed
from app.models.filter import ArticleDomain, ArticleKeyword
from app.schemas.article import ArticleResponse
from app.schemas.common import ResponseModel
from app.services.filter_service import FilterService
from app.utils.time_utils import is_within_days, get_configured_time

logger = logging.getLogger(__name__)
router = APIRouter()

# 每个来源只取该天数内的文章，此条件优先于 push_count
TODAY_MAX_DAYS = 3


def _get_feed_name_cache(db: Session) -> dict:
    """预加载所有 feed 名称，避免 N+1 查询"""
    feeds = db.query(RSSFeed.id, RSSFeed.name).all()
    return {f.id: f.name for f in feeds}


def _build_article_response(article: RSSItem, feed_name: str, today_str: str) -> dict:
    """构建单篇文章的响应体"""
    is_new = (article.first_crawl_time == today_str) if article.first_crawl_time else False
    return {
        "id": article.id,
        "title": article.title,
        "source": feed_name,
        "feedName": feed_name,
        "summary": article.summary or "",
        "url": article.url,
        "publishedAt": article.published_at or "",
        "pushedAt": article.last_crawl_time or "",
        "isRead": bool(article.is_read),
        "isNew": is_new,
    }


@router.get("/today")
def get_today_articles(
    domain_id: Optional[int] = Query(None),
    keywords: Optional[str] = Query(None),
    exclude_keywords: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取当日入库文章，不做过滤（过滤已在 fetch 阶段完成）"""
    today_str = get_configured_time().strftime("%Y-%m-%d")
    feed_names = _get_feed_name_cache(db)

    articles = db.query(RSSItem).filter(
        RSSItem.first_crawl_time == today_str
    ).order_by(desc(RSSItem.published_at), desc(RSSItem.created_at)).all()

    if not articles:
        return {
            "code": 0,
            "message": "当日暂无文章，请点击「抓取」按钮获取最新内容",
            "data": {"articles": [], "total": 0, "filterTier": "none"}
        }

    seen_urls = set()
    deduped = []
    for a in articles:
        if a.url in seen_urls:
            continue
        seen_urls.add(a.url)
        deduped.append(a)

    result = [
        _build_article_response(a, feed_names.get(a.feed_id, ""), today_str)
        for a in deduped
    ]
    logger.info("[today] 返回 %d 条（当日入库，去重后）", len(result))
    return {
        "code": 0,
        "message": "success",
        "data": {"articles": result, "total": len(result), "filterTier": "none"}
    }


@router.get("/today/debug")
def debug_today_articles(db: Session = Depends(get_db)):
    """诊断接口：分析 /today 为什么没有返回文章"""
    today = date.today()
    today_str = get_configured_time().strftime("%Y-%m-%d")
    feed_names = _get_feed_name_cache(db)

    report = {
        "systemTime": {
            "date_today": str(today),
            "datetime_now": str(datetime.now()),
            "today_str": today_str,
        },
        "queries": {},
        "feeds": [],
        "filterDomains": [],
        "sampleArticles": [],
    }

    # 各查询策略的命中数量
    count_a = db.query(func.count(RSSItem.id)).filter(
        RSSItem.first_crawl_time == today_str
    ).scalar()
    count_b = db.query(func.count(RSSItem.id)).filter(
        cast(RSSItem.created_at, Date) == today
    ).scalar()
    total = db.query(func.count(RSSItem.id)).scalar()

    report["queries"] = {
        "first_crawl_time_today": count_a,
        "created_at_date_today": count_b,
        "total_articles": total,
    }

    # 各来源的文章数量
    feed_stats = db.query(
        RSSItem.feed_id, func.count(RSSItem.id)
    ).group_by(RSSItem.feed_id).all()
    for fid, cnt in feed_stats:
        today_cnt = db.query(func.count(RSSItem.id)).filter(
            RSSItem.feed_id == fid,
            RSSItem.first_crawl_time == today_str
        ).scalar()
        report["feeds"].append({
            "feedId": fid,
            "feedName": feed_names.get(fid, fid),
            "totalArticles": cnt,
            "todayArticles": today_cnt,
        })

    # 过滤域信息
    domains = db.query(ArticleDomain).all()
    for d in domains:
        kw_count = db.query(func.count(ArticleKeyword.id)).filter(
            ArticleKeyword.domain_id == d.id
        ).scalar()
        req_count = db.query(func.count(ArticleKeyword.id)).filter(
            ArticleKeyword.domain_id == d.id,
            ArticleKeyword.is_required == True
        ).scalar()
        neg_count = db.query(func.count(ArticleKeyword.id)).filter(
            ArticleKeyword.domain_id == d.id,
            ArticleKeyword.keyword_type == "negative"
        ).scalar()
        report["filterDomains"].append({
            "id": d.id,
            "name": d.name,
            "enabled": d.enabled,
            "totalKeywords": kw_count,
            "requiredKeywords": req_count,
            "negativeKeywords": neg_count,
        })

    # 最新 5 篇文章样本
    latest = db.query(RSSItem).order_by(desc(RSSItem.created_at)).limit(5).all()
    for a in latest:
        report["sampleArticles"].append({
            "id": a.id,
            "title": (a.title or "")[:80],
            "feedId": a.feed_id,
            "feedName": feed_names.get(a.feed_id, ""),
            "first_crawl_time": a.first_crawl_time,
            "created_at": str(a.created_at) if a.created_at else None,
            "published_at": a.published_at,
        })

    return {"code": 0, "message": "diagnostic", "data": report}


@router.get("/history")
def get_history_articles(
    date_filter: Optional[str] = Query(None, alias="date"),
    domain_id: Optional[int] = Query(None),
    keywords: Optional[str] = Query(None),
    exclude_keywords: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    apply_filter: bool = Query(True, description="是否应用默认过滤规则（只返回已过滤的文章）"),
    db: Session = Depends(get_db)
):
    """获取历史推送（默认只返回已通过过滤的文章）"""
    today_str = get_configured_time().strftime("%Y-%m-%d")
    feed_names = _get_feed_name_cache(db)

    query = db.query(RSSItem).join(
        RSSFeed, RSSItem.feed_id == RSSFeed.id
    )

    if date_filter:
        query = query.filter(RSSItem.first_crawl_time == date_filter)

    if apply_filter:
        query = query.filter(RSSItem.domain_id.isnot(None))

    articles = query.order_by(desc(RSSItem.created_at)).all()

    if domain_id:
        filtered = FilterService.filter_articles(articles, domain_id, db)
        articles = [item[0] for item in filtered]

    if keywords or exclude_keywords:
        pos_kw = keywords.split(",") if keywords else None
        neg_kw = exclude_keywords.split(",") if exclude_keywords else None
        articles = FilterService.filter_by_keywords(articles, pos_kw, neg_kw)

    total = len(articles)

    offset = (page - 1) * pageSize
    paginated_articles = articles[offset:offset + pageSize]

    result = [
        _build_article_response(a, feed_names.get(a.feed_id, ""), today_str)
        for a in paginated_articles
    ]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "articles": result,
            "total": total,
            "page": page,
            "pageSize": pageSize
        }
    }


@router.post("/mark-read/{articleId}")
def mark_article_read(articleId: int, db: Session = Depends(get_db)):
    """标记文章已读"""
    article = db.query(RSSItem).filter(RSSItem.id == articleId).first()

    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    article.is_read = True
    db.commit()

    return {
        "code": 0,
        "message": "标记成功",
        "data": {"success": True}
    }
