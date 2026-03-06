# coding=utf-8
"""测试邮件推送：使用今日文章和选题发送到指定邮箱"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_db_context
from app.utils.time_utils import get_configured_time
from app.models.article import RSSItem
from app.models.feed import RSSFeed
from app.models.ai import BlogTopic, TopicReference
from app.models.subscriber import EmailSubscriber
from app.services.crawler_service import fetch_all_active_feeds
from app.services.ai_service import get_ai_service
from app.services.email_service import send_digest
from sqlalchemy import desc


def _get_today_articles(db, limit=50):
    today_str = get_configured_time().strftime("%Y-%m-%d")
    return db.query(RSSItem).filter(
        RSSItem.first_crawl_time == today_str
    ).order_by(desc(RSSItem.published_at), desc(RSSItem.created_at)).limit(limit).all()


def _get_today_topics(db, today_str):
    topics = db.query(BlogTopic).filter(BlogTopic.date == today_str).order_by(BlogTopic.id).all()
    result = []
    for t in topics:
        refs = db.query(TopicReference).filter(TopicReference.topic_id == t.id).all()
        result.append({
            "title": t.title,
            "reason": t.description,
            "relatedArticles": [{"title": r.article_title, "url": r.article_url, "source": r.source or ""} for r in refs]
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="测试邮件推送")
    parser.add_argument("-e", "--email", help="测试邮箱，不指定则用 email_subscribers 或 TEST_EMAIL")
    args = parser.parse_args()

    to_emails = []
    if args.email:
        to_emails = [args.email.strip()]
    else:
        test_email = getattr(settings, "TEST_EMAIL", None) or os.environ.get("TEST_EMAIL")
        if test_email:
            to_emails = [e.strip() for e in test_email.split(",") if e.strip()]
        if not to_emails:
            with get_db_context() as db:
                subs = db.query(EmailSubscriber.email).filter(EmailSubscriber.is_active == 1).all()
                to_emails = [s[0] for s in subs]
    if not to_emails:
        print("❌ 未指定邮箱，请使用 -e xxx@example.com 或配置 TEST_EMAIL")
        sys.exit(1)

    with get_db_context() as db:
        today_str = get_configured_time().strftime("%Y-%m-%d")
        feed_names = {f.id: f.name for f in db.query(RSSFeed).all()}
        articles = _get_today_articles(db)
        topics = _get_today_topics(db, today_str)

        if not articles:
            print("今日无文章，正在抓取 RSS...")
            fetch_all_active_feeds(db, max_feeds=0)
            articles = _get_today_articles(db)
        if not articles:
            print("❌ 抓取后仍无今日文章")
            sys.exit(1)
        if not topics:
            print("今日无选题，正在生成...")
            rss_items = [
                {"title": a.title, "title_zh": getattr(a, "title_zh", None), "url": a.url, "feed_id": feed_names.get(a.feed_id, ""), "summary": a.summary or ""}
                for a in articles
            ]
            topic_result = get_ai_service().generate_topics(rss_items)
            if topic_result.success and topic_result.topics:
                from app.services.scheduler_service import _save_topics_to_db
                _save_topics_to_db(db, topic_result.topics, today_str, len(articles))
                topics = _get_today_topics(db, today_str)
        if not topics:
            print("❌ 无选题可推送")
            sys.exit(1)

        article_dicts = [
            {"title": a.title, "title_zh": getattr(a, "title_zh", None), "url": a.url, "source": feed_names.get(a.feed_id, "")}
            for a in articles
        ]
        print(f"推送 {len(article_dicts)} 篇文章、{len(topics)} 个选题到 {len(to_emails)} 个邮箱...")

    sent = send_digest(to_emails, article_dicts, topics, today_str)
    print(f"✅ 已发送 {sent}/{len(to_emails)} 封")
    sys.exit(0 if sent == len(to_emails) else 1)


if __name__ == "__main__":
    main()
