# coding=utf-8
"""
统一 RSS 抓取服务：SourceConfig → Entry[]，fetch_status 分类，per-source 代理/冷却/条件 GET。
"""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from app.core import http_client as hc
from app.core.config import settings
from app.core.crawler.parser import RSSParser, ParsedRSSItem

from . import rsshub_resolver
from . import medium_source

logger = logging.getLogger(__name__)

FETCH_STATUS_OK = "OK"
FETCH_STATUS_TIMEOUT = "TIMEOUT"
FETCH_STATUS_RESET = "RESET"
FETCH_STATUS_HTTP_403 = "HTTP_403"
FETCH_STATUS_HTTP_5XX = "HTTP_5XX"
FETCH_STATUS_INVALID_XML = "INVALID_XML"
FETCH_STATUS_EMPTY_FEED = "EMPTY_FEED"

COOLDOWN_HOURS_403 = 6


@dataclass
class SourceConfig:
    id: str
    name: str
    type: str  # rss | rsshub | medium
    url: str
    enabled: bool = True
    use_proxy: Optional[bool] = None  # None = inherit from global
    refresh_interval_minutes: int = 30
    tags: list = field(default_factory=list)
    cooldown_until: Optional[datetime] = None
    last_etag: Optional[str] = None
    last_modified: Optional[str] = None


@dataclass
class Entry:
    source_id: str
    source_name: str
    title: str
    link: str
    published_at: str
    author: str = ""
    summary: str = ""
    content: str = ""
    guid: str = ""
    tags: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class FetchResult:
    entries: list[Entry]
    fetch_status: str
    elapsed_ms: int = 0
    error_message: Optional[str] = None
    final_url: Optional[str] = None
    not_modified: bool = False


def _guid_for_entry(parsed: ParsedRSSItem, link: str) -> str:
    if parsed.guid:
        return str(parsed.guid).strip()[:512]
    return hashlib.sha256(link.encode()).hexdigest()[:16]


def _parsed_to_entry(parsed: ParsedRSSItem, source_id: str, source_name: str, tags: list) -> Entry:
    link = parsed.url or ""
    return Entry(
        source_id=source_id,
        source_name=source_name,
        title=parsed.title or "",
        link=link,
        published_at=parsed.published_at or "",
        author=parsed.author or "",
        summary=(parsed.summary or "")[:2000],
        guid=_guid_for_entry(parsed, link),
        tags=list(tags),
        raw={},
    )


def _resolve_url_and_proxy(source: SourceConfig) -> tuple[str, bool]:
    """返回 (final_url, use_proxy)。"""
    use_proxy_global = getattr(settings, "RSS_USE_PROXY", False)
    use_proxy = source.use_proxy if source.use_proxy is not None else use_proxy_global
    url = source.url

    if source.type == "medium":
        try:
            res = medium_source.resolve_medium_source()
            if res:
                return res.url, res.use_proxy
        except NotImplementedError:
            raise
        return url, use_proxy

    if source.type == "rsshub":
        resolved = rsshub_resolver.resolve_rsshub_url(source.url)
        if resolved:
            url = resolved
        return url, use_proxy

    return url, use_proxy


def _session_for_proxy(use_proxy: bool) -> requests.Session:
    return hc.create_session(
        use_proxy=use_proxy,
        proxy_url=getattr(settings, "RSS_PROXY_URL", "") or "",
        proxy_https_url=getattr(settings, "RSS_PROXY_HTTPS_URL", "") or "",
        no_proxy=getattr(settings, "RSS_NO_PROXY", "") or "",
        retries=getattr(settings, "RSS_HTTP_RETRIES", 1),
        headers=hc.RSS_HEADERS,
    )


def _classify_error(exc: Exception, status_code: Optional[int]) -> str:
    if status_code == 403:
        return FETCH_STATUS_HTTP_403
    if status_code and 500 <= status_code < 600:
        return FETCH_STATUS_HTTP_5XX
    if isinstance(exc, requests.Timeout):
        return FETCH_STATUS_TIMEOUT
    if isinstance(exc, (requests.ConnectionError, ConnectionError)):
        msg = str(exc).lower()
        if "reset" in msg or "connection" in msg:
            return FETCH_STATUS_RESET
    return "ERROR"


def fetch_one(
    source: SourceConfig,
    connect_timeout: Optional[int] = None,
    read_timeout: Optional[int] = None,
) -> FetchResult:
    """
    抓取单个源，返回 Entry 列表与 fetch_status。
    若 source.cooldown_until 未过期则跳过（返回 EMPTY_FEED + 无条目）。
    支持 If-None-Match / If-Modified-Since，304 视为 OK 且 entries 为空。
    """
    if not source.enabled:
        return FetchResult(entries=[], fetch_status=FETCH_STATUS_OK, error_message="disabled")

    now = datetime.now(timezone.utc)
    if source.cooldown_until and source.cooldown_until.tzinfo is None:
        from app.utils.time_utils import DEFAULT_TIMEZONE
        import zoneinfo
        tz = zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)
        cooldown_aware = source.cooldown_until.replace(tzinfo=tz)
    else:
        cooldown_aware = source.cooldown_until
    if cooldown_aware and now < cooldown_aware:
        logger.info("[rss_fetcher] %s skipped: in cooldown until %s", source.id, cooldown_aware)
        return FetchResult(entries=[], fetch_status=FETCH_STATUS_OK, error_message="cooldown")

    try:
        url, use_proxy = _resolve_url_and_proxy(source)
    except NotImplementedError:
        return FetchResult(
            entries=[],
            fetch_status="ERROR",
            error_message="MEDIUM_MODE=api not implemented",
        )

    connect_timeout = connect_timeout or getattr(settings, "RSS_HTTP_CONNECT_TIMEOUT", 10)
    read_timeout = read_timeout or getattr(settings, "RSS_HTTP_READ_TIMEOUT", 30)
    session = _session_for_proxy(use_proxy)

    headers = {}
    if source.last_etag:
        headers["If-None-Match"] = source.last_etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified
    if headers:
        session.headers.update(headers)

    urls_to_try = [url]
    if source.type == "rsshub":
        fallback_bases = rsshub_resolver.get_rsshub_fallback_base_urls()
        for base in fallback_bases:
            urls_to_try.append(rsshub_resolver.build_rsshub_url_with_base(base, source.url))

    last_error: Optional[str] = None
    last_status: Optional[str] = None
    last_elapsed = 0
    last_final_url: Optional[str] = None
    resp = None

    for try_url in urls_to_try:
        try:
            resp, elapsed_ms = hc.get(try_url, session=session, connect_timeout=connect_timeout, read_timeout=read_timeout)
        except requests.Timeout as e:
            last_error = str(e)
            last_status = FETCH_STATUS_TIMEOUT
            last_elapsed = 0
            continue
        except requests.RequestException as e:
            last_error = str(e)
            last_status = _classify_error(e, getattr(e, "response", None) and getattr(e.response, "status_code", None))
            last_elapsed = 0
            continue
        last_elapsed = elapsed_ms
        last_final_url = resp.url or try_url
        if resp.status_code == 200:
            break
        if resp.status_code == 304:
            break
        last_error = f"HTTP {resp.status_code}"
        if resp.status_code == 403:
            last_status = FETCH_STATUS_HTTP_403
            break
        if 500 <= resp.status_code < 600:
            last_status = FETCH_STATUS_HTTP_5XX
        else:
            last_status = "HTTP_" + str(resp.status_code)
    else:
        if last_status and last_error:
            return FetchResult(
                entries=[],
                fetch_status=last_status,
                error_message=last_error,
                elapsed_ms=last_elapsed,
                final_url=last_final_url,
            )
        resp = None

    if resp is None:
        return FetchResult(
            entries=[],
            fetch_status=last_status or "ERROR",
            error_message=last_error or "no response",
            elapsed_ms=last_elapsed,
            final_url=last_final_url,
        )

    elapsed_ms = last_elapsed
    final_url = last_final_url or resp.url or url
    status_code = resp.status_code

    if status_code == 403:
        logger.warning("[rss_fetcher] %s HTTP_403", source.id)
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_HTTP_403,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
            error_message="403 Forbidden",
        )
    if 500 <= status_code < 600:
        logger.warning("[rss_fetcher] %s HTTP_5XX status=%s", source.id, status_code)
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_HTTP_5XX,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
            error_message=f"HTTP {status_code}",
        )
    if status_code == 304:
        logger.info("[rss_fetcher] %s 304 Not Modified elapsed=%dms", source.id, elapsed_ms)
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_OK,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
            not_modified=True,
        )

    resp.raise_for_status()
    text = resp.text
    if not text or not text.strip():
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_EMPTY_FEED,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
            error_message="empty body",
        )

    parser = RSSParser()
    try:
        parsed_list = parser.parse(text, final_url)
    except ValueError as e:
        logger.warning("[rss_fetcher] %s INVALID_XML: %s", source.id, e)
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_INVALID_XML,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
            error_message=str(e),
        )

    if not parsed_list:
        return FetchResult(
            entries=[],
            fetch_status=FETCH_STATUS_EMPTY_FEED,
            elapsed_ms=elapsed_ms,
            final_url=final_url,
        )

    entries = [_parsed_to_entry(p, source.id, source.name, source.tags) for p in parsed_list]
    logger.info("[rss_fetcher] %s OK entries=%d elapsed=%dms", source.id, len(entries), elapsed_ms)
    return FetchResult(
        entries=entries,
        fetch_status=FETCH_STATUS_OK,
        elapsed_ms=elapsed_ms,
        final_url=final_url,
    )


def fetch_all_sources(
    sources: list[SourceConfig],
    connect_timeout: Optional[int] = None,
    read_timeout: Optional[int] = None,
) -> dict[str, FetchResult]:
    """并发抓取所有源，单源失败不影响其他。返回 source_id -> FetchResult。"""
    results: dict[str, FetchResult] = {}
    for src in sources:
        try:
            results[src.id] = fetch_one(src, connect_timeout=connect_timeout, read_timeout=read_timeout)
        except Exception as e:
            logger.warning("[rss_fetcher] %s exception: %s", src.id, e)
            results[src.id] = FetchResult(
                entries=[],
                fetch_status="ERROR",
                error_message=str(e),
            )
    return results
