# coding=utf-8
"""单 URL 网页抓取，抽取 title 与 summary。优先使用 trafilatura 正文抽取。"""
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from app.core import http_client as hc
from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_DIR: Path | None = None


def _get_cache_dir() -> Path | None:
    global _CACHE_DIR
    if _CACHE_DIR is None:
        base = Path(__file__).resolve().parent.parent.parent
        d = base / ".fetch_cache"
        try:
            d.mkdir(parents=True, exist_ok=True)
            _CACHE_DIR = d
        except OSError:
            _CACHE_DIR = None
    return _CACHE_DIR


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def fetch_url(url: str, max_summary_chars: int = 2000) -> dict[str, Any]:
    """
    抓取 URL 并抽取 title 与正文摘要。

    Returns:
        {"url": str, "title": str, "summary": str}
        失败时 title/summary 为占位，不抛异常。
    """
    logger.info("[fetch] START url=%s", url)
    out: dict[str, Any] = {"url": url, "title": url, "summary": ""}
    cache_dir = _get_cache_dir()
    if cache_dir:
        ck = _cache_key(url)
        cache_file = cache_dir / f"{ck}.json"
        try:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                logger.info("[fetch] CACHE HIT url=%s", url)
                return {**out, **cached}
        except Exception as e:
            logger.debug("[fetch] cache read skip: %s", e)

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

    body = _extract_body_text(html, url)
    if body:
        out["summary"] = body[:max_summary_chars]
    if cache_dir:
        try:
            cache_file = cache_dir / f"{_cache_key(url)}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"title": out["title"], "summary": out["summary"]}, f, ensure_ascii=False)
        except Exception as e:
            logger.debug("[fetch] cache write skip: %s", e)
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


def _extract_body_text(html: str, url: str = "") -> str:
    try:
        import trafilatura
        text = trafilatura.extract(html, url=url or None, include_comments=False, include_tables=True)
        if text and len(text.strip()) > 100:
            return text.strip()
    except Exception as e:
        logger.debug("[fetch] trafilatura fallback: %s", e)
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
