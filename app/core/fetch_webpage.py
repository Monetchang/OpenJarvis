# coding=utf-8
"""单 URL 网页抓取，抽取 title 与 summary。"""
import logging
import re
from typing import Any

from app.core import http_client as hc
from app.core.config import settings

logger = logging.getLogger(__name__)


def fetch_url(url: str, max_summary_chars: int = 2000) -> dict[str, Any]:
    """
    抓取 URL 并抽取 title 与正文摘要。

    Returns:
        {"url": str, "title": str, "summary": str}
        失败时 title/summary 为占位，不抛异常。
    """
    logger.info("[fetch] START url=%s", url)
    out: dict[str, Any] = {"url": url, "title": url, "summary": ""}

    session = hc.create_session(
        use_proxy=settings.RSS_USE_PROXY,
        proxy_url=settings.RSS_PROXY_URL,
        proxy_https_url=settings.RSS_PROXY_HTTPS_URL,
        no_proxy=settings.RSS_NO_PROXY,
        retries=settings.RSS_HTTP_RETRIES,
        headers=hc.BROWSER_HEADERS,
    )

    try:
        resp, _ = hc.get(
            url,
            session=session,
            connect_timeout=settings.RSS_HTTP_CONNECT_TIMEOUT,
            read_timeout=settings.RSS_HTTP_READ_TIMEOUT,
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning("[fetch] FAIL url=%s error=%s", url, e)
        return out

    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
    if title_match:
        out["title"] = _clean_text(title_match.group(1))

    body = _extract_body_text(html)
    if body:
        out["summary"] = body[:max_summary_chars]
    logger.info(
        "[fetch] OK url=%s status=%d title=%s summary_len=%d",
        url, resp.status_code, (out["title"] or "")[:80], len(out["summary"]),
    )
    return out


def _clean_text(text: str) -> str:
    import html as html_module
    text = html_module.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body_text(html: str) -> str:
    for tag in ("script", "style", "nav", "header", "footer", "aside", "noscript"):
        html = re.sub(rf"<{tag}[^>]*>[\s\S]*?</{tag}>", "", html, flags=re.I)
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", html, re.I)
        if m:
            block = m.group(1)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 100:
                return text
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
