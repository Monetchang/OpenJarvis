# coding=utf-8
"""
RSS 定时抓取调度：抓取 -> 生成选题 -> 邮件推送
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import get_db_context
from app.core.config import settings
from app.models.article import RSSItem
from app.models.feed import RSSFeed
from app.models.subscriber import EmailSubscriber
from app.services.crawler_service import fetch_all_active_feeds
from app.services.ai_service import get_ai_service
from app.services.email_service import send_digest

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()
JOB_ID = "rss_fetch"


def _get_today_articles(db: Session, limit: int = 50) -> list:
    """获取当日入库文章（过滤已在 fetch 完成，直接按时间取）"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    articles = db.query(RSSItem).filter(
        RSSItem.first_crawl_time == today_str
    ).order_by(desc(RSSItem.published_at), desc(RSSItem.created_at)).limit(limit).all()
    return list(articles)


def run_digest_job(force_fetch: bool = True, skip_when_no_fetch: bool = False) -> dict:
    """
    执行一次完整流程：抓取 -> 生成选题 -> 邮件推送
    PUSH_TEST_MODE=True 时：仅抓 1 个源、跳过选题、文章限 10 条
    """
    test_mode = getattr(settings, "PUSH_TEST_MODE", False)
    with get_db_context() as db:
        today_str = datetime.now().strftime("%Y-%m-%d")
        feed_names = {f.id: f.name for f in db.query(RSSFeed).all()}
        fetched = 0
        if force_fetch:
            result = fetch_all_active_feeds(db, max_feeds=1 if test_mode else 0)
            if result.get("success"):
                fetched = result.get("total_items", 0)
            logger.info("[digest] 抓取完成: %d 条%s", fetched, " (测试模式)" if test_mode else "")
            if skip_when_no_fetch and fetched == 0:
                return {"success": False, "fetched": 0, "articles": 0, "topics": 0, "sent": 0}
        articles = _get_today_articles(db, limit=10 if test_mode else 50)
        logger.info("[digest] 今日文章: %d 条", len(articles))
        if not articles:
            return {"success": False, "fetched": fetched, "articles": 0, "topics": 0, "sent": 0}
        article_dicts = [
            {"title": a.title, "url": a.url, "source": feed_names.get(a.feed_id, "")}
            for a in articles
        ]
        topics = []
        rss_items = [
            {"title": a.title, "url": a.url, "feed_id": feed_names.get(a.feed_id, ""), "summary": a.summary or ""}
            for a in articles
        ]
        ai = get_ai_service()
        logger.info("[digest] 生成选题中...")
        topic_result = ai.generate_topics(rss_items)
        if topic_result.success and topic_result.topics:
            raw = topic_result.topics[:1] if test_mode else topic_result.topics
            for t in raw:
                topics.append({
                    "title": t.title,
                    "reason": t.description,
                    "relatedArticles": getattr(t, "related_articles", []) or []
                })
        subscribers = db.query(EmailSubscriber.email).filter(EmailSubscriber.is_active == 1).all()
        to_emails = [s[0] for s in subscribers]
        logger.info("[digest] 订阅邮箱: %d 个 %s", len(to_emails), to_emails[:3] if to_emails else [])
        sent = 0
        if to_emails:
            sent = send_digest(to_emails, article_dicts, topics, today_str)
            logger.info("[digest] 邮件已推送到 %d/%d 个邮箱", sent, len(to_emails))
        else:
            logger.warning("[digest] 无订阅邮箱，跳过推送")
        return {"success": True, "fetched": fetched, "articles": len(articles), "topics": len(topics), "sent": sent}


def run_fetch_only_job():
    """仅抓取，不推邮件。用于启动预抓取、冷启动补数据。"""
    with get_db_context() as db:
        result = fetch_all_active_feeds(db, max_feeds=0)
        if result.get("success"):
            logger.info("[startup_fetch] 预抓取完成: %d 条", result.get("total_items", 0))
        else:
            logger.info("[startup_fetch] 预抓取跳过: %s", result.get("error", "unknown"))


def _run_job():
    result = run_digest_job(force_fetch=True, skip_when_no_fetch=False)
    if not result["success"]:
        logger.info("[scheduler] 无可用文章，跳过推送")
    else:
        logger.info("[scheduler] 已推送到 %d 个邮箱", result.get("sent", 0))


def init_scheduler(cron_expr: str):
    _scheduler.add_job(_run_job, CronTrigger.from_crontab(cron_expr), id=JOB_ID)
    if getattr(settings, "STARTUP_PREFETCH_ENABLED", True):
        _scheduler.add_job(
            run_fetch_only_job,
            "date",
            run_date=datetime.now() + timedelta(seconds=15),
            id="startup_fetch",
        )
    _scheduler.start()


def reschedule(cron_expr: str):
    _scheduler.reschedule_job(JOB_ID, trigger=CronTrigger.from_crontab(cron_expr))


def shutdown():
    _scheduler.shutdown(wait=False)
