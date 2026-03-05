# coding=utf-8
"""
RSSHub URL 解析：base_url + route → 最终 RSS URL，支持多实例 fallback。
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _base_urls() -> list[str]:
    urls = []
    if settings.RSSHUB_BASE_URL:
        urls.append(settings.RSSHUB_BASE_URL.rstrip("/"))
    fallback = getattr(settings, "RSSHUB_FALLBACK_BASE_URLS", "") or ""
    for u in fallback.split(","):
        u = u.strip().rstrip("/")
        if u and u not in urls:
            urls.append(u)
    return urls


def resolve_rsshub_url(route_or_url: str) -> Optional[str]:
    """
    将 RSSHub route 或完整 URL 解析为可抓取的 RSS URL。
    route 示例: /medium/tag/artificial-intelligence
    若为完整 URL（以 http 开头），原样返回（由调用方决定是否用 fallback 重试）。
    依次尝试 base_urls，返回第一个拼接结果（不在此处发请求，仅拼 URL）。
    若 RSSHub 未启用或无 base，返回 None。
    """
    if not getattr(settings, "RSSHUB_ENABLED", False):
        return None
    base_list = _base_urls()
    if not base_list:
        return None
    path = route_or_url.strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base_list[0] + path


def get_rsshub_fallback_base_urls() -> list[str]:
    """返回除主 base 外的 fallback base 列表，用于失败时重试。"""
    bases = _base_urls()
    return bases[1:] if len(bases) > 1 else []


def build_rsshub_url_with_base(base: str, route_or_url: str) -> str:
    """用指定 base 拼出完整 RSS URL。"""
    base = base.rstrip("/")
    path = route_or_url.strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path
