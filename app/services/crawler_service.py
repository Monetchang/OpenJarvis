# coding=utf-8
"""
RSS 爬虫服务层

封装 RSS 抓取和处理功能
"""
import logging
import time
import threading
from typing import List, Dict, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from types import SimpleNamespace

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.core.crawler import RSSFetcher, RSSFeedConfig

_fetch_lock = threading.Lock()


def _filterable_item(feed_id: str, item: Any, title: str, summary: str) -> SimpleNamespace:
    """构建供 FilterService 使用的对象（需有 title/summary/feed_id/published_at）"""
    return SimpleNamespace(
        title=title,
        summary=summary or "",
        feed_id=feed_id,
        published_at=item.published_at or "",
        _item=item,
        _feed_id=feed_id,
    )


def _needs_translation(text: str) -> bool:
    """判断文本是否需要翻译（CJK 占比 < 25% 视为英文）"""
    if not text or not text.strip():
        return False
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af")
    return cjk / max(len(text), 1) < 0.25
from app.models.feed import RSSFeed
from app.models.article import RSSItem as RSSItemDB
from app.utils.config_db import get_config_value


class CrawlerService:
    """RSS 爬虫服务"""

    def __init__(self):
        """初始化爬虫服务"""
        self.timeout = settings.RSS_TIMEOUT
        self.request_interval = settings.RSS_REQUEST_INTERVAL

    def fetch_feeds(
        self,
        feeds: List[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """
        抓取 RSS 源，翻译后经关键词过滤，仅通过过滤的文章入库
        """
        t0 = time.time()

        # Step1: 构建配置
        feed_configs = []
        for feed in feeds:
            max_items = feed.get("max_items", 0)
            max_age_days = feed.get("max_age_days", 3)
            feed_config = RSSFeedConfig(
                id=feed.get("id", ""),
                name=feed.get("name", ""),
                url=feed.get("url", ""),
                max_items=max_items,
                enabled=feed.get("enabled", True),
                max_age_days=max_age_days,
            )
            if feed_config.id and feed_config.url:
                feed_configs.append(feed_config)

        if not feed_configs:
            return {"success": False, "error": "没有有效的 RSS 源配置"}
        logger.info("[fetch] Step1 构建配置 耗时=%.2fs", time.time() - t0)

        # Step2: 清空当日（synchronize_session=False 避免与后续修改的 existing 对象冲突）
        t_step = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        deleted = db.query(RSSItemDB).filter(RSSItemDB.first_crawl_time == today).delete(
            synchronize_session=False
        )
        if deleted:
            logger.info("[fetch] Step2 清空当日 %d 条 耗时=%.2fs", deleted, time.time() - t_step)
        else:
            logger.info("[fetch] Step2 清空当日(0条) 耗时=%.2fs", time.time() - t_step)

        # Step3: RSS 抓取
        fetcher = RSSFetcher(
            feeds=feed_configs,
            request_interval=self.request_interval,
            timeout=settings.RSS_HTTP_READ_TIMEOUT,
            connect_timeout=settings.RSS_HTTP_CONNECT_TIMEOUT,
            use_proxy=settings.RSS_USE_PROXY,
            proxy_url=settings.RSS_PROXY_URL,
            proxy_https_url=settings.RSS_PROXY_HTTPS_URL,
            no_proxy=settings.RSS_NO_PROXY,
            retries=settings.RSS_HTTP_RETRIES,
            timezone=settings.TIMEZONE,
            freshness_enabled=True,
            default_max_age_days=3,
            max_concurrent=settings.RSS_MAX_CONCURRENT,
        )
        t_step = time.time()
        rss_data = fetcher.fetch_all()
        logger.info("[fetch] Step3 RSS抓取 耗时=%.2fs 共 %d 源 %d 条",
                    time.time() - t_step, len(rss_data.items), sum(len(v) for v in rss_data.items.values()))

        # Step4: 收集 + 一次性批量翻译（新文+补翻合并）
        t_step = time.time()
        logger.info("[fetch] Step4 开始 收集 new_items 与 backfill")
        all_new_items: List[tuple] = []
        items_needing_trans: List[tuple] = []
        backfill_records: List[RSSItemDB] = []
        title_map: Dict[tuple, str] = {}
        summary_map: Dict[tuple, str] = {}
        trusted_feed_ids: Set[str] = {
            f.id for f in db.query(RSSFeed.id).filter(RSSFeed.is_trusted == 1).all()
        }

        for idx, (feed_id, items) in enumerate(rss_data.items.items()):
            feed_db = db.query(RSSFeed).filter(RSSFeed.id == feed_id).first()
            if feed_db:
                feed_db.last_fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                feed_db.last_fetch_status = "success"
                feed_db.item_count = len(items)

            urls = [item.url for item in items]
            existing_urls = set(
                row[0] for row in db.query(RSSItemDB.url).filter(
                    RSSItemDB.feed_id == feed_id,
                    RSSItemDB.url.in_(urls)
                ).all()
            )
            new_items = [item for item in items if item.url not in existing_urls]
            existing_items = [item for item in items if item.url in existing_urls]

            trans_enabled = bool(
                get_config_value(db, "translation_enabled", settings.TRANSLATION_ENABLED)
                or (feed_db and feed_db.enable_translation)
            )

            for item in new_items:
                all_new_items.append((feed_id, item))
                if trans_enabled and _needs_translation(item.title or ""):
                    items_needing_trans.append((feed_id, item))

            if trans_enabled and existing_items:
                for item in existing_items:
                    if len(backfill_records) >= 20:
                        break
                    rec = db.query(RSSItemDB).filter(
                        RSSItemDB.url == item.url,
                        RSSItemDB.feed_id == feed_id,
                    ).first()
                    if rec and _needs_translation(rec.title or ""):
                        backfill_records.append(rec)

            for item in existing_items:
                existing = db.query(RSSItemDB).filter(
                    RSSItemDB.url == item.url,
                    RSSItemDB.feed_id == feed_id
                ).first()
                if existing:
                    existing.crawl_count += 1
                    existing.last_crawl_time = datetime.now().strftime("%H:%M")

        t_collect = time.time() - t_step
        logger.info("[fetch] Step4 收集完成 耗时=%.2fs new=%d backfill=%d",
                    t_collect, len(items_needing_trans), len(backfill_records))

        all_titles: List[str] = []
        all_summaries: List[str] = []
        all_titles.extend(item.title or "" for _, item in items_needing_trans)
        all_summaries.extend(item.summary or "" for _, item in items_needing_trans)
        all_titles.extend(r.title or "" for r in backfill_records)
        all_summaries.extend(r.summary or "" for r in backfill_records)

        TRANS_CHUNK = 50

        def _translate_and_fill(texts: List[str], dest_new: list, dest_backfill: list) -> None:
            all_results = []
            for chunk_start in range(0, len(texts), TRANS_CHUNK):
                chunk = texts[chunk_start:chunk_start + TRANS_CHUNK]
                t0 = time.time()
                bt = ai.translate_batch(chunk)
                logger.info("[fetch] Step4 翻译批次 %d-%d 耗时=%.2fs",
                           chunk_start, chunk_start + len(chunk), time.time() - t0)
                all_results.extend(bt.results)
            n_new = len(items_needing_trans)
            for i, (fid, it) in enumerate(dest_new):
                if i < len(all_results) and all_results[i].success and all_results[i].translated_text:
                    title_map[(fid, it.url)] = all_results[i].translated_text
            for i, rec in enumerate(dest_backfill):
                idx = n_new + i
                if idx < len(all_results) and all_results[idx].success and all_results[idx].translated_text:
                    rec.title = all_results[idx].translated_text

        def _translate_summaries_and_fill(texts: List[str], dest_new: list, dest_backfill: list) -> None:
            all_results = []
            for chunk_start in range(0, len(texts), TRANS_CHUNK):
                chunk = texts[chunk_start:chunk_start + TRANS_CHUNK]
                t0 = time.time()
                bs = ai.translate_batch(chunk)
                logger.info("[fetch] Step4 翻译批次 summaries %d-%d 耗时=%.2fs",
                           chunk_start, chunk_start + len(chunk), time.time() - t0)
                all_results.extend(bs.results)
            n_new = len(items_needing_trans)
            for i, (fid, it) in enumerate(dest_new):
                if i < len(all_results) and all_results[i].success and all_results[i].translated_text:
                    summary_map[(fid, it.url)] = all_results[i].translated_text
            for i, rec in enumerate(dest_backfill):
                idx = n_new + i
                if idx < len(all_results) and all_results[idx].success and all_results[idx].translated_text:
                    rec.summary = all_results[idx].translated_text

        if all_titles or all_summaries:
            try:
                from app.services.ai_service import get_ai_service
                ai = get_ai_service()
                if all_titles:
                    t_trans = time.time()
                    logger.info("[fetch] Step4 开始批量翻译 titles 共 %d 条 (分%d批)",
                                len(all_titles), (len(all_titles) + TRANS_CHUNK - 1) // TRANS_CHUNK)
                    _translate_and_fill(all_titles, items_needing_trans, backfill_records)
                    logger.info("[fetch] Step4 titles 全部完成 耗时=%.2fs", time.time() - t_trans)
                if all_summaries:
                    t_trans = time.time()
                    logger.info("[fetch] Step4 开始批量翻译 summaries 共 %d 条 (分%d批)",
                                len(all_summaries), (len(all_summaries) + TRANS_CHUNK - 1) // TRANS_CHUNK)
                    _translate_summaries_and_fill(all_summaries, items_needing_trans, backfill_records)
                    logger.info("[fetch] Step4 summaries 全部完成 耗时=%.2fs", time.time() - t_trans)
            except Exception as e:
                logger.warning("抓取时翻译失败: %s", e)

        new_items_to_save = []
        for feed_id, item in all_new_items:
            title = title_map.get((feed_id, item.url)) or item.title
            summary = summary_map.get((feed_id, item.url)) or item.summary
            new_items_to_save.append((feed_id, item, title, summary))

        logger.info("[fetch] Step4 翻译完成 耗时=%.2fs 待过滤 new_items=%d",
                    time.time() - t_step, len(new_items_to_save))

        # Step5: 关键词过滤（两阶段管道）
        t_step = time.time()
        from app.models.filter import ArticleKeyword
        from app.services.filter_service import FilterService

        passed_items: List[tuple] = []
        filter_tier = "n/a"
        if new_items_to_save:
            filterables = [
                _filterable_item(fid, it, tit, summ)
                for fid, it, tit, summ in new_items_to_save
            ]
            neg_keywords = db.query(ArticleKeyword).filter(
                ArticleKeyword.keyword_type == "negative"
            ).all()
            filtered_list, filter_tier = FilterService.two_phase_pipeline(
                filterables, neg_keywords, trusted_feed_ids=trusted_feed_ids, db=db
            )
            passed_urls = {(f._feed_id, f._item.url) for f in filtered_list}
            passed_items = [(fid, it, tit, summ) for fid, it, tit, summ in new_items_to_save
                          if (fid, it.url) in passed_urls]
        logger.info("[fetch] Step5 关键词过滤 耗时=%.2fs 通过 %d/%d 条 tier=%s",
                    time.time() - t_step, len(passed_items), len(new_items_to_save), filter_tier)

        # Step6: 入库
        t_step = time.time()
        total_items = len(passed_items)
        for feed_id, item, title, summary in passed_items:
            db_item = RSSItemDB(
                title=title,
                feed_id=feed_id,
                url=item.url,
                published_at=item.published_at,
                summary=summary,
                author=item.author,
                first_crawl_time=today,
                last_crawl_time=datetime.now().strftime("%H:%M"),
                crawl_count=1,
                is_read=False
            )
            db.add(db_item)
        logger.info("[fetch] Step6 入库 %d 条 耗时=%.2fs", total_items, time.time() - t_step)

        # Step7: commit
        t_step = time.time()
        try:
            db.commit()
        except StaleDataError as e:
            db.rollback()
            logger.warning("[fetch] Step7 commit 失败(StaleDataError)，可能因外部删除了 rss_items: %s", e)
            return {
                "success": False,
                "error": "数据已被并发修改（如执行了 seed 替换源），请刷新后重试",
                "total_feeds": len(feed_configs),
                "success_feeds": len(rss_data.items),
                "failed_feeds": len(rss_data.failed_ids),
                "total_items": 0,
                "date": rss_data.date,
                "crawl_time": rss_data.crawl_time,
            }
        logger.info("[fetch] Step7 commit 耗时=%.2fs", time.time() - t_step)

        result = {
            "success": True,
            "total_feeds": len(feed_configs),
            "success_feeds": len(rss_data.items),
            "failed_feeds": len(rss_data.failed_ids),
            "total_items": total_items,
            "date": rss_data.date,
            "crawl_time": rss_data.crawl_time
        }
        logger.info("[fetch] 完成 总耗时=%.2fs result=%s", time.time() - t0, result)
        return result

    def validate_rss_url(self, url: str) -> bool:
        """
        验证 RSS URL 是否可访问

        Args:
            url: RSS URL

        Returns:
            bool: 是否可访问
        """
        import requests
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return True
        except Exception:
            return False


def fetch_all_active_feeds(db: Session, max_feeds: int = 0) -> Dict[str, Any]:
    """从数据库读取启用的 RSS 源并执行抓取。max_feeds>0 时仅抓前 N 个（测试用）"""
    acquired = _fetch_lock.acquire(blocking=False)
    if not acquired:
        logger.info("[fetch] 已有抓取任务在运行，跳过本次触发")
        return {"success": False, "error": "已有抓取任务在运行，请稍后重试"}

    try:
        feeds = db.query(RSSFeed).filter(RSSFeed.is_active == 1).all()
        if max_feeds > 0:
            feeds = feeds[:max_feeds]
        feed_list = [
            {
                "id": f.id,
                "name": f.name,
                "url": f.feed_url,
                "max_items": f.push_count or 10,
                "max_age_days": 90 if f.is_trusted else 30,
            }
            for f in feeds
        ]
        return get_crawler_service().fetch_feeds(feed_list, db)
    finally:
        _fetch_lock.release()


# 全局单例
_crawler_service_instance = None


def get_crawler_service() -> CrawlerService:
    """获取爬虫服务单例"""
    global _crawler_service_instance
    if _crawler_service_instance is None:
        _crawler_service_instance = CrawlerService()
    return _crawler_service_instance

