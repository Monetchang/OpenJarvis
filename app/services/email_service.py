# coding=utf-8
"""
邮件推送服务

优先使用 Resend（仅需 RESEND_API_KEY），否则回退 SMTP
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_digest_html(articles: List[Dict], topics: List[Dict], date_str: str) -> str:
    """构建日报 HTML"""
    articles_html = ""
    for a in articles:
        articles_html += f"""
        <li style="margin-bottom:12px;">
            <a href="{a.get('url','')}" style="color:#2563eb;text-decoration:none;">{a.get('title','')}</a>
            <span style="color:#6b7280;font-size:12px;"> · {a.get('source','')}</span>
        </li>"""
    topics_html = ""
    for t in topics:
        refs = t.get("relatedArticles", [])
        ref_str = "".join(f'<a href="{r.get("url","")}" style="color:#6b7280;font-size:12px;">{r.get("title","")}</a> ' for r in refs[:3])
        topics_html += f"""
        <div style="margin-bottom:16px;padding:12px;background:#f9fafb;border-radius:8px;">
            <div style="font-weight:600;margin-bottom:4px;">{t.get("title","")}</div>
            <div style="color:#4b5563;font-size:14px;">{t.get("reason","")}</div>
            <div style="margin-top:8px;font-size:12px;">{ref_str}</div>
        </div>"""
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:24px;">
<h2 style="color:#111;">OpenJarvis 每日推送 · {date_str}</h2>
<h3 style="color:#374151;">今日文章</h3>
<ul style="list-style:none;padding:0;">{articles_html}</ul>
<h3 style="color:#374151;">AI 选题建议</h3>
{topics_html}
<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
<p style="color:#9ca3af;font-size:12px;">由 OpenJarvis 自动推送 · 取消订阅请联系管理员</p>
</body>
</html>"""


def send_digest(to_emails: List[str], articles: List[Dict], topics: List[Dict], date_str: str) -> int:
    """
    发送日报到指定邮箱列表
    Returns: 成功发送数量
    """
    if not to_emails:
        return 0
    html = _build_digest_html(articles, topics, date_str)
    subject = f"OpenJarvis 每日推送 · {date_str}"

    if settings.RESEND_API_KEY:
        logger.info("[email] 使用 Resend 发送到 %d 个邮箱", len(to_emails))
        return _send_via_resend(to_emails, subject, html)
    if all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD, settings.SMTP_FROM]):
        return _send_via_smtp(to_emails, subject, html)
    logger.warning("未配置 RESEND_API_KEY 或 SMTP，跳过邮件推送")
    return 0


def _send_via_resend(to_emails: List[str], subject: str, html: str) -> int:
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        sent = 0
        for addr in to_emails:
            try:
                resend.Emails.send({
                    "from": settings.RESEND_FROM,
                    "to": [addr],
                    "subject": subject,
                    "html": html,
                })
                sent += 1
                logger.info("[email] 已发送到 %s", addr)
            except Exception as e:
                logger.warning("Resend 发送到 %s 失败: %s", addr, e)
        logger.info("[email] Resend 共发送 %d/%d", sent, len(to_emails))
        return sent
    except Exception as e:
        logger.error("Resend 发送失败: %s", e)
        return 0


def _send_via_smtp(to_emails: List[str], subject: str, html: str) -> int:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg.attach(MIMEText(html, "html", "utf-8"))
    sent = 0
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            for addr in to_emails:
                try:
                    msg["To"] = addr
                    smtp.sendmail(settings.SMTP_FROM, addr, msg.as_string())
                    sent += 1
                except Exception as e:
                    logger.warning("发送到 %s 失败: %s", addr, e)
    except Exception as e:
        logger.error("SMTP 发送失败: %s", e)
    return sent
