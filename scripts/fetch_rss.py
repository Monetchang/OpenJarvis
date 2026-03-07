# coding=utf-8
"""
手动触发RSS抓取
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db_context
from app.models.feed import RSSFeed
from app.models.article import RSSItem
from app.core.crawler.fetcher import RSSFetcher, RSSFeedConfig
from app.core.config import settings
from app.services.ai_service import get_ai_service
from datetime import datetime

def fetch_all_feeds():
    """抓取所有RSS源"""
    with get_db_context() as db:
        # 获取所有活跃的订阅源
        feeds = db.query(RSSFeed).filter(RSSFeed.is_active == 1).all()
        
        if not feeds:
            print("❌ 没有活跃的订阅源")
            return
        
        print(f"📡 开始抓取 {len(feeds)} 个RSS源...\n")
        
        # 转换为RSSFeedConfig
        feed_configs = []
        for feed in feeds:
            if not feed.feed_url:
                print(f"⚠️  跳过 {feed.name}: 没有URL")
                continue
                
            config = RSSFeedConfig(
                id=feed.id,
                name=feed.name,
                url=feed.feed_url,
                enabled=True,
                max_items=0,  # 0 表示随机 3-5 篇
                max_age_days=3  # 只获取 3 天内的文章
            )
            feed_configs.append(config)
        
        # 创建抓取器
        fetcher = RSSFetcher(
            feeds=feed_configs,
            request_interval=settings.RSS_REQUEST_INTERVAL,
            timeout=settings.RSS_HTTP_READ_TIMEOUT,
            connect_timeout=settings.RSS_HTTP_CONNECT_TIMEOUT,
            use_proxy=settings.RSS_USE_PROXY,
            proxy_url=settings.RSS_PROXY_URL,
            proxy_https_url=settings.RSS_PROXY_HTTPS_URL,
            no_proxy=settings.RSS_NO_PROXY,
            retries=settings.RSS_HTTP_RETRIES,
            timezone=settings.TIMEZONE,
            freshness_enabled=True,
            default_max_age_days=3
        )
        
        # 抓取所有源
        rss_data = fetcher.fetch_all()
        
        # 获取AI翻译服务
        ai_service = get_ai_service() if settings.TRANSLATION_ENABLED else None
        
        # 保存到数据库
        total_saved = 0
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        crawl_time = now.strftime("%H:%M")
        
        for feed_id, items in rss_data.items.items():
            print(f"\n📰 {feed_id}: {len(items)} 篇文章")
            
            # 批量收集需要翻译的标题
            titles_to_translate = []
            items_to_save = []
            
            for item in items:
                # 检查是否已存在
                existing = db.query(RSSItem).filter(
                    RSSItem.feed_id == feed_id,
                    RSSItem.url == item.url
                ).first()
                
                if existing:
                    # 更新抓取时间
                    existing.last_crawl_time = crawl_time
                    continue
                
                items_to_save.append(item)
                titles_to_translate.append(item.title)
            
            # 批量翻译标题
            translated_titles = {}
            if ai_service and titles_to_translate:
                print(f"   🔄 翻译 {len(titles_to_translate)} 个标题...")
                batch_result = ai_service.translate_batch(titles_to_translate)
                for i, result in enumerate(batch_result.results):
                    if result.translated_text:
                        translated_titles[titles_to_translate[i]] = result.translated_text
            
            # 保存新文章（title=原文，title_zh=翻译）
            for item in items_to_save:
                title_zh = translated_titles.get(item.title) if translated_titles else None
                db_item = RSSItem(
                    feed_id=feed_id,
                    title=item.title or "",
                    title_zh=title_zh,
                    url=item.url,
                    summary=item.summary or "",
                    author=item.author or "",
                    published_at=item.published_at or "",
                    first_crawl_time=crawl_time,
                    last_crawl_time=crawl_time,
                    is_read=False
                )
                db.add(db_item)
                total_saved += 1
            
        db.commit()
        
        print(f"\n{'='*50}")
        print(f"✅ 抓取完成！")
        print(f"📊 总计: {sum(len(items) for items in rss_data.items.values())} 篇文章")
        print(f"💾 新增: {total_saved} 篇")
        print(f"{'='*50}")

if __name__ == "__main__":
    fetch_all_feeds()

