# coding=utf-8
"""
诊断失败的 RSS 源，测试不同 UA/Header 组合，输出原因与建议。
用法: python scripts/diagnose_feeds.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time

TARGETS = [
    ("MarkTechPost",    "https://www.marktechpost.com/feed/",                   "403"),
    ("AI News",         "https://www.artificialintelligence-news.com/feed/",    "403"),
    ("Google AI Blog",  "https://ai.googleblog.com/feeds/posts/default?alt=rss","404"),
    ("Sebastian Raschka","https://sebastianraschka.com/rss.xml",               "404"),
    ("Papers with Code","https://paperswithcode.com/latest.rss",               "parse_error"),
]

UA_VARIANTS = [
    ("curl",       "curl/7.88.1"),
    ("python",     "python-requests/2.31.0"),
    ("chrome_mac", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("chrome_win", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    ("feedparser", "FeedParser/6.0"),
    ("googlebot",  "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
]

ACCEPT_VARIANTS = [
    ("rss_accept",  "application/rss+xml, application/xml, text/xml, */*"),
    ("html_accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("any_accept",  "*/*"),
]

PROXIES = None  # 需要代理时改为 {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

COLOR_OK    = "\033[32m"
COLOR_FAIL  = "\033[31m"
COLOR_WARN  = "\033[33m"
COLOR_RESET = "\033[0m"


def probe(url: str, ua: str, accept: str, proxies=None, timeout=10) -> tuple[int, str]:
    """返回 (status_code, content_type)，异常返回 (-1, error_msg)"""
    headers = {
        "User-Agent": ua,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
    }
    try:
        r = requests.get(url, headers=headers, proxies=proxies, timeout=timeout, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        return r.status_code, ct
    except requests.exceptions.ConnectionError as e:
        return -1, f"ConnectionError: {e}"
    except requests.exceptions.Timeout:
        return -1, "Timeout"
    except Exception as e:
        return -1, str(e)


def check_redirect(url: str, ua: str) -> str:
    """追踪重定向链"""
    headers = {"User-Agent": ua, "Accept": "*/*"}
    try:
        r = requests.get(url, headers=headers, proxies=PROXIES, timeout=10, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            return f"-> {r.headers.get('Location', '?')}"
        return f"no redirect ({r.status_code})"
    except Exception as e:
        return f"error: {e}"


def diagnose(name: str, url: str, expected_issue: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  {url}")
    print(f"  预期问题: {expected_issue}")
    print(f"{'='*60}")

    # 1. 用最简单的 chrome UA + rss accept 先试
    status, ct = probe(url, UA_VARIANTS[2][1], ACCEPT_VARIANTS[0][1], PROXIES)
    print(f"\n[基准测试] status={status} content-type={ct[:60] if ct else '-'}")

    if status == 404:
        # 检查是否有重定向
        redirect = check_redirect(url, UA_VARIANTS[2][1])
        print(f"[重定向检查] {redirect}")
        _suggest_404(name, url)
        return

    if status == -1:
        print(f"{COLOR_FAIL}[网络错误] {ct}{COLOR_RESET}")
        return

    if status == 200:
        print(f"{COLOR_OK}[基准通过 200] 无需进一步测试{COLOR_RESET}")
        _check_content(url, UA_VARIANTS[2][1])
        return

    if status == 403:
        print(f"\n[UA 矩阵测试] 尝试不同 User-Agent...")
        working_ua = None
        for ua_name, ua_str in UA_VARIANTS:
            s, c = probe(url, ua_str, ACCEPT_VARIANTS[0][1], PROXIES)
            mark = f"{COLOR_OK}✓{COLOR_RESET}" if s == 200 else f"{COLOR_FAIL}✗{COLOR_RESET}"
            print(f"  {mark} [{ua_name:12s}] status={s}")
            if s == 200 and not working_ua:
                working_ua = (ua_name, ua_str)
            time.sleep(0.5)

        if working_ua:
            print(f"\n{COLOR_OK}[结论] UA '{working_ua[0]}' 可绕过 403{COLOR_RESET}")
            print(f"  建议: 将 http_client.py 的 RSS_HEADERS User-Agent 改为:\n  {working_ua[1]}")
        else:
            print(f"\n[Accept 矩阵测试] 尝试不同 Accept...")
            for acc_name, acc_str in ACCEPT_VARIANTS:
                s, c = probe(url, UA_VARIANTS[2][1], acc_str, PROXIES)
                mark = f"{COLOR_OK}✓{COLOR_RESET}" if s == 200 else f"{COLOR_FAIL}✗{COLOR_RESET}"
                print(f"  {mark} [{acc_name:12s}] status={s}")
                time.sleep(0.5)

            print(f"\n{COLOR_WARN}[结论] 所有 UA/Accept 组合均失败，可能原因:{COLOR_RESET}")
            print("  1. Cloudflare / 反爬机制，需要完整 TLS 指纹（requests 无法绕过）")
            print("  2. 需要 Referer 或 Cookie")
            print("  3. IP 被封禁（需换代理 IP）")
            print(f"  建议: 考虑替换为其他同类信源，或使用 RSSHub 中转")


def _check_content(url: str, ua: str):
    """200 但内容异常时诊断"""
    headers = {"User-Agent": ua, "Accept": "*/*"}
    try:
        r = requests.get(url, headers=headers, proxies=PROXIES, timeout=10)
        content = r.text[:200].strip()
        if "<html" in content.lower():
            print(f"{COLOR_WARN}[内容警告] 返回 HTML 而非 RSS/XML，可能被重定向到登录页或 Cloudflare 挑战页{COLOR_RESET}")
            print(f"  内容片段: {content[:100]}")
        elif "<?xml" in content or "<rss" in content or "<feed" in content:
            print(f"{COLOR_OK}[内容正常] 是有效 XML/RSS{COLOR_RESET}")
        else:
            print(f"{COLOR_WARN}[内容未知] {content[:100]}{COLOR_RESET}")
    except Exception as e:
        print(f"内容检查失败: {e}")


def _suggest_404(name: str, url: str):
    suggestions = {
        "Google AI Blog":    "已迁移至 https://blog.google/technology/ai/ ，RSS: https://blog.google/technology/ai/rss/",
        "Sebastian Raschka": "个人博客地址已变更，可尝试 https://sebastianraschka.com/blog/index.html 查找最新 RSS 链接",
    }
    s = suggestions.get(name)
    if s:
        print(f"{COLOR_WARN}[建议] {s}{COLOR_RESET}")
    else:
        print(f"{COLOR_WARN}[建议] URL 已失效，需手动查找新的 RSS 地址{COLOR_RESET}")


if __name__ == "__main__":
    print("RSS 源诊断工具")
    print(f"代理: {PROXIES or '未启用（如需代理请修改脚本顶部 PROXIES 变量）'}")

    for name, url, issue in TARGETS:
        diagnose(name, url, issue)

    print(f"\n{'='*60}")
    print("诊断完成")
