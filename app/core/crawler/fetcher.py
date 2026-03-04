# coding=utf-8
"""
RSS 抓取器

负责从配置的 RSS 源抓取数据并转换为标准格式
"""

import logging
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import requests

from .parser import RSSParser, ParsedRSSItem
from app.core import http_client as hc
from app.utils.time_utils import get_configured_time, is_within_days, DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)


@dataclass
class RSSFeedConfig:
    """RSS 源配置"""
    id: str                     # 源 ID
    name: str                   # 显示名称
    url: str                    # RSS URL
    max_items: int = 0          # 最大条目数（0=不限制）
    enabled: bool = True        # 是否启用
    max_age_days: Optional[int] = None  # 文章最大年龄（天），覆盖全局设置；None=使用全局，0=禁用过滤


@dataclass
class RSSItem:
    """RSS 条目数据模型（简化版，用于抓取）"""
    title: str
    feed_id: str
    feed_name: str = ""
    url: str = ""
    published_at: str = ""
    summary: str = ""
    author: str = ""
    crawl_time: str = ""
    first_time: str = ""
    last_time: str = ""
    count: int = 1


@dataclass
class RSSData:
    """RSS 数据集合"""
    date: str
    crawl_time: str
    items: Dict[str, List[RSSItem]]
    id_to_name: Dict[str, str]
    failed_ids: List[str]


class RSSFetcher:
    """RSS 抓取器"""

    _tl = threading.local()

    def __init__(
        self,
        feeds: List[RSSFeedConfig],
        request_interval: int = 2000,
        timeout: int = 15,
        connect_timeout: int = 10,
        use_proxy: bool = False,
        proxy_url: str = "",
        proxy_https_url: str = "",
        no_proxy: str = "",
        retries: int = 1,
        timezone: str = DEFAULT_TIMEZONE,
        freshness_enabled: bool = True,
        default_max_age_days: int = 3,
        max_concurrent: int = 5,
    ):
        """
        初始化抓取器

        Args:
            feeds: RSS 源配置列表
            request_interval: 请求间隔（毫秒）
            timeout: 请求超时（秒）
            use_proxy: 是否使用代理
            proxy_url: 代理 URL
            timezone: 时区配置（如 'Asia/Shanghai'）
            freshness_enabled: 是否启用新鲜度过滤
            default_max_age_days: 默认最大文章年龄（天）
            max_concurrent: 最大并发抓取数
        """
        self.feeds = [f for f in feeds if f.enabled]
        self.request_interval = request_interval
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.proxy_https_url = proxy_https_url
        self.no_proxy = no_proxy
        self.retries = retries
        self.timezone = timezone
        self.freshness_enabled = freshness_enabled
        self.default_max_age_days = default_max_age_days
        self.max_concurrent = max(1, max_concurrent)

        self.parser = RSSParser()

    def _get_session(self) -> requests.Session:
        if not getattr(self._tl, "session", None):
            self._tl.session = self._create_session()
        return self._tl.session

    def _create_session(self) -> requests.Session:
        return hc.create_session(
            use_proxy=self.use_proxy,
            proxy_url=self.proxy_url,
            proxy_https_url=self.proxy_https_url,
            no_proxy=self.no_proxy,
            retries=self.retries,
            headers=hc.RSS_HEADERS,
        )

    def _filter_by_freshness(
        self,
        items: List[RSSItem],
        feed: RSSFeedConfig,
    ) -> Tuple[List[RSSItem], int]:
        """
        根据新鲜度过滤文章

        Args:
            items: 待过滤的文章列表
            feed: RSS 源配置

        Returns:
            (过滤后的文章列表, 被过滤的文章数)
        """
        # 如果全局禁用，直接返回
        if not self.freshness_enabled:
            return items, 0

        # 确定此 feed 的 max_age_days
        max_days = feed.max_age_days
        if max_days is None:
            max_days = self.default_max_age_days

        # 如果设为 0，禁用此 feed 的过滤
        if max_days == 0:
            return items, 0

        # 过滤逻辑：无发布时间的文章保留
        filtered = []
        for item in items:
            if not item.published_at:
                # 无发布时间，保留
                filtered.append(item)
            elif is_within_days(item.published_at, max_days, self.timezone):
                # 在指定天数内，保留
                filtered.append(item)
            # 否则过滤掉

        filtered_count = len(items) - len(filtered)
        return filtered, filtered_count

    def fetch_feed(self, feed: RSSFeedConfig) -> Tuple[List[RSSItem], Optional[str]]:
        """
        抓取单个 RSS 源

        Args:
            feed: RSS 源配置

        Returns:
            (条目列表, 错误信息) 元组
        """
        try:
            response = hc.get(
                feed.url,
                session=self._get_session(),
                connect_timeout=self.connect_timeout,
                read_timeout=self.timeout,
            )
            response.raise_for_status()

            parsed_items = self.parser.parse(response.text, feed.url)

            # 转换为 RSSItem（使用配置的时区）
            now = get_configured_time(self.timezone)
            crawl_time = now.strftime("%H:%M")
            items = []

            for parsed in parsed_items:
                item = RSSItem(
                    title=parsed.title,
                    feed_id=feed.id,
                    feed_name=feed.name,
                    url=parsed.url,
                    published_at=parsed.published_at or "",
                    summary=parsed.summary or "",
                    author=parsed.author or "",
                    crawl_time=crawl_time,
                    first_time=crawl_time,
                    last_time=crawl_time,
                    count=1,
                )
                items.append(item)

            # 应用日期过滤（如果有日期）
            if items:
                items, filtered_count = self._filter_by_freshness(items, feed)
            if filtered_count > 0:
                logger.info("[RSS] %s: 日期过滤掉 %d 条", feed.name, filtered_count)

            # 限制条目数量：每个源最多 3-5 篇（如果未指定 max_items）
            if feed.max_items == 0:
                # 随机选择 3-5 篇
                import random
                max_items = random.randint(3, 5)
                if len(items) > max_items:
                    items = items[:max_items]
            elif feed.max_items > 0:
                # 使用配置的 max_items
                if len(items) > feed.max_items:
                    items = items[:feed.max_items]

            logger.info("[RSS] %s: 获取 %d 条", feed.name, len(items))

            return items, None

        except requests.Timeout:
            error = f"请求超时 ({self.timeout}s)"
            logger.warning("[RSS] %s: %s", feed.name, error)
            return [], error

        except requests.RequestException as e:
            error = f"请求失败: {e}"
            logger.warning("[RSS] %s: %s", feed.name, error)
            return [], error

        except ValueError as e:
            error = f"解析失败: {e}"
            logger.warning("[RSS] %s: %s", feed.name, error)
            return [], error

        except Exception as e:
            error = f"未知错误: {e}"
            logger.warning("[RSS] %s: %s", feed.name, error)
            return [], error

    def fetch_all(self) -> RSSData:
        """
        抓取所有 RSS 源（并发，受 max_concurrent 限制）
        """
        all_items: Dict[str, List[RSSItem]] = {}
        id_to_name: Dict[str, str] = {}
        failed_ids: List[str] = []

        now = get_configured_time(self.timezone)
        crawl_time = now.strftime("%H:%M")
        crawl_date = now.strftime("%Y-%m-%d")

        logger.info("[RSS] 开始抓取 %d 个 RSS 源 (并发数=%d)", len(self.feeds), self.max_concurrent)

        workers = min(self.max_concurrent, len(self.feeds))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_feed = {executor.submit(self.fetch_feed, feed): feed for feed in self.feeds}
            for future in as_completed(future_to_feed):
                feed = future_to_feed[future]
                id_to_name[feed.id] = feed.name
                try:
                    items, error = future.result()
                    if error:
                        failed_ids.append(feed.id)
                    else:
                        all_items[feed.id] = items
                except Exception as e:
                    failed_ids.append(feed.id)
                    logger.warning("[RSS] %s: %s", feed.name, e)

        total_items = sum(len(items) for items in all_items.values())
        logger.info("[RSS] 抓取完成: %d 个源成功, %d 个失败, 共 %d 条", len(all_items), len(failed_ids), total_items)

        return RSSData(
            date=crawl_date,
            crawl_time=crawl_time,
            items=all_items,
            id_to_name=id_to_name,
            failed_ids=failed_ids,
        )

