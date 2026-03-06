# coding=utf-8
"""
统一 HTTP 客户端

代理、超时、UA 统一管理，供 RSS 抓取与 fetch_url 共用。
"""
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# 对以下域名额外打印代理/超时日志
_NOTABLE_DOMAINS = (
    "medium.com",
    "lilianweng.github.io",
    "artificialintelligence-news.com",
)

RSS_HEADERS: dict = {
    # FeedParser UA 被多数站点白名单识别为合法 RSS 阅读器，避免被反爬拦截
    # macOS Chrome UA 会被 MarkTechPost / AI News 等站点返回 403
    "User-Agent": "FeedParser/6.0.8 +https://github.com/kurtmckee/feedparser",
    "Accept": (
        "application/feed+json, application/json, application/rss+xml, "
        "application/atom+xml, application/xml, text/xml, */*"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BROWSER_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _proxy_scheme(proxy_url: str) -> str:
    """从 proxy_url 提取协议类型，如 http / socks5h"""
    if not proxy_url:
        return "none"
    for scheme in ("socks5h", "socks5", "socks4a", "socks4", "https", "http"):
        if proxy_url.startswith(scheme + "://"):
            return scheme
    return "unknown"


def _is_notable(url: str) -> bool:
    return any(d in url for d in _NOTABLE_DOMAINS)


def _session_proxy_url(session: requests.Session) -> str:
    """从 session 里取出实际生效的代理地址"""
    proxies = getattr(session, "proxies", {}) or {}
    return proxies.get("https") or proxies.get("http") or ""


def create_session(
    use_proxy: bool = False,
    proxy_url: str = "",
    proxy_https_url: str = "",
    no_proxy: str = "",
    retries: int = 1,
    headers: dict | None = None,
) -> requests.Session:
    """
    创建 requests.Session。

    Args:
        use_proxy: 是否启用代理
        proxy_url: http/https/socks5h 代理地址（同时用于 http 和 https，除非 proxy_https_url 指定）
        proxy_https_url: 仅覆盖 https 代理，留空则与 proxy_url 相同
        no_proxy: 不走代理的域名，逗号分隔
        retries: 重试次数
        headers: 请求头，留空使用 RSS_HEADERS
    """
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(headers or RSS_HEADERS)

    if use_proxy and proxy_url:
        session.proxies = {
            "http": proxy_url,
            "https": proxy_https_url or proxy_url,
        }
        if no_proxy:
            session.proxies["no"] = no_proxy

    return session


def get(
    url: str,
    session: requests.Session,
    connect_timeout: int = 10,
    read_timeout: int = 10,
) -> tuple[requests.Response, int]:
    """
    通过已配置的 session 发起 GET 请求。
    返回 (response, elapsed_ms)。
    对 notable domain 自动打印代理类型与超时参数。
    """
    if _is_notable(url):
        effective_proxy = _session_proxy_url(session)
        logger.info(
            "[http] url=%s use_proxy=%s proxy_type=%s connect_timeout=%ss read_timeout=%ss",
            url,
            bool(effective_proxy),
            _proxy_scheme(effective_proxy),
            connect_timeout,
            read_timeout,
        )
    t0 = time.perf_counter()
    resp = session.get(url, timeout=(connect_timeout, read_timeout))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return resp, elapsed_ms
