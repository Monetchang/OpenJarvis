# coding=utf-8
"""测试飞书推送：使用今日文章和选题推送到 .env 中的 FEISHU_WEBHOOK_URL"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_db_context
from app.utils.time_utils import get_configured_time
from app.models.article import RSSItem
from app.models.feed import RSSFeed
from app.models.ai import BlogTopic, TopicReference
from app.services.crawler_service import fetch_all_active_feeds
from app.services.ai_service import get_ai_service
from app.services.feishu import feishu_service
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
    urls = [u.strip() for u in (settings.FEISHU_WEBHOOK_URL or "").split(";") if u.strip()]
    if not urls:
        print("❌ 未配置 FEISHU_WEBHOOK_URL，请在 .env 中设置")
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
        print(f"推送 {len(article_dicts)} 篇文章、{len(topics)} 个选题到 {len(urls)} 个 webhook...")

    ok = 0
    for i, url in enumerate(urls):
        display_url = url[:60] + "..." if len(url) > 60 else url
        if feishu_service.send_digest_to_webhook(url, article_dicts, topics, today_str):
            print(f"  [{i+1}] ✅ {display_url}")
            ok += 1
        else:
            print(f"  [{i+1}] ❌ {display_url}")
    print(f"\n结果: {ok}/{len(urls)} 成功")
    sys.exit(0 if ok == len(urls) else 1)


if __name__ == "__main__":
    main()
