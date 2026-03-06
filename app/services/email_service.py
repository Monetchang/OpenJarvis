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


def _article_display_title(a: Dict) -> str:
    """中英文标题：有 title_zh 且与 title 不同时显示「中文 (English)」"""
    title = a.get("title", "")
    title_zh = a.get("title_zh") or ""
    if title_zh and title_zh.strip() and title_zh != title:
        return f"{title_zh} ({title})"
    return title


def _build_digest_html(articles: List[Dict], topics: List[Dict], date_str: str) -> str:
    """构建日报 HTML，带色块与分区样式"""
    articles_html = ""
    for i, a in enumerate(articles, 1):
        disp = _article_display_title(a)
        articles_html += f"""
        <li style="margin-bottom:14px;padding:10px 12px;background:#f8fafc;border-radius:6px;border-left:3px solid #3b82f6;">
            <a href="{a.get('url','')}" style="color:#1e40af;text-decoration:none;font-weight:500;">{disp}</a>
            <span style="color:#64748b;font-size:12px;display:block;margin-top:4px;">{a.get('source','')}</span>
        </li>"""
    topics_html = ""
    for t in topics:
        refs = t.get("relatedArticles", [])[:5]
        ref_items = "".join(
            f'<a href="{r.get("url","")}" style="color:#64748b;font-size:12px;text-decoration:none;display:inline-block;margin:2px 8px 2px 0;">· {r.get("title","")}</a>'
            for r in refs
        )
        ref_block = f'<div style="margin-top:10px;padding-top:8px;border-top:1px dashed #bae6fd;">{ref_items}</div>' if ref_items else ""
        topics_html += f"""
        <div style="margin-bottom:16px;padding:16px;background:linear-gradient(135deg,#f0f9ff 0%,#e0f2fe 100%);border-radius:8px;border-left:4px solid #0ea5e9;">
            <div style="font-weight:700;font-size:15px;color:#0c4a6e;margin-bottom:8px;">{t.get("title","")}</div>
            <div style="color:#475569;font-size:14px;line-height:1.5;">{t.get("reason","")}</div>
            {ref_block}
        </div>"""
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:640px;margin:0 auto;padding:24px;background:#f1f5f9;">
<div style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);">
  <div style="background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%);color:#fff;padding:20px 24px;">
    <h1 style="margin:0;font-size:20px;font-weight:600;">OpenJarvis 每日推送</h1>
    <p style="margin:8px 0 0;font-size:14px;opacity:.9;">{date_str}</p>
  </div>
  <div style="padding:24px;">
    <div style="display:inline-block;background:#dbeafe;color:#1e40af;font-weight:600;font-size:13px;padding:6px 12px;border-radius:6px;margin-bottom:16px;">📰 今日文章</div>
    <ul style="list-style:none;padding:0;margin:0;">{articles_html}</ul>
    <div style="display:inline-block;background:#e0f2fe;color:#0c4a6e;font-weight:600;font-size:13px;padding:6px 12px;border-radius:6px;margin:24px 0 16px;">💡 AI 选题建议</div>
    {topics_html}
  </div>
  <div style="background:#f8fafc;padding:12px 24px;text-align:center;color:#94a3b8;font-size:12px;">由 OpenJarvis 自动推送 · 取消订阅请联系管理员</div>
</div>
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
