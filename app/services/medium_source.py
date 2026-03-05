# coding=utf-8
"""
Medium 源策略：rss_proxy（强制代理拉 RSS）| rsshub | api（预留 stub）。
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

from . import rsshub_resolver

logger = logging.getLogger(__name__)

MEDIUM_RSSHUB_ROUTE = "/medium/tag/artificial-intelligence"


@dataclass
class MediumResolveResult:
    url: str
    use_proxy: bool
    source: str  # "rss_proxy" | "rsshub" | "api"


def resolve_medium_source() -> Optional[MediumResolveResult]:
    """
    根据 MEDIUM_MODE 解析 Medium 源的抓取 URL 与是否走代理。
    rss_proxy: 使用 MEDIUM_RSS_URL，强制 use_proxy=True
    rsshub: 使用 RSSHub route，use_proxy 由全局/源配置决定
    api: 暂不实现，抛出 NotImplementedError 并提示
    """
    mode = (getattr(settings, "MEDIUM_MODE", None) or "rss_proxy").strip().lower()
    if mode == "rss_proxy":
        url = getattr(settings, "MEDIUM_RSS_URL", "") or "https://medium.com/feed/tag/artificial-intelligence"
        return MediumResolveResult(url=url, use_proxy=True, source="rss_proxy")
    if mode == "rsshub":
        base_urls = rsshub_resolver._base_urls()
        if not base_urls:
            logger.warning("[medium] MEDIUM_MODE=rsshub but no RSSHUB_BASE_URL configured")
            return None
        url = rsshub_resolver.build_rsshub_url_with_base(base_urls[0], MEDIUM_RSSHUB_ROUTE)
        return MediumResolveResult(url=url, use_proxy=False, source="rsshub")
    if mode == "api":
        raise NotImplementedError(
            "MEDIUM_MODE=api is not implemented. Use rss_proxy or rsshub, or configure MEDIUM_API_TOKEN/MEDIUM_API_BASE_URL when supported."
        )
    logger.warning("[medium] unknown MEDIUM_MODE=%s, fallback to rss_proxy", mode)
    url = getattr(settings, "MEDIUM_RSS_URL", "") or "https://medium.com/feed/tag/artificial-intelligence"
    return MediumResolveResult(url=url, use_proxy=True, source="rss_proxy")
