import httpx
import json
import logging
import time
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

FEISHU_WEBHOOK_PREFIX_BOT = "https://open.feishu.cn/open-apis/bot/v2/hook/"
FEISHU_WEBHOOK_PREFIX_FLOW = "https://www.feishu.cn/flow/api/trigger-webhook/"


class FeishuService:
    def __init__(self):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        self._access_token = None
        self._token_expire_time = 0
    
    async def get_access_token(self) -> str:
        """获取访问令牌"""
        if not self.app_id or not self.app_secret:
            raise ValueError("Feishu app_id and app_secret must be configured")
        
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            data = response.json()
            self._access_token = data.get("tenant_access_token")
            self._token_expire_time = time.time() + data.get("expire", 7200) - 300
            return self._access_token
    
    async def send_message(self, chat_id: str, msg_type: str, content: Dict):
        """发送消息到群组"""
        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": chat_id,
                    "msg_type": msg_type,
                    "content": json.dumps(content)
                }
            )
            return response.json()
    
    async def update_card(self, token: str, card: Dict):
        """更新消息卡片"""
        access_token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/im/v1/messages/update_card",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "token": token,
                    "card": card
                }
            )
            return response.json()
    
    def build_topic_card(self, topics: List[Dict[str, Any]]) -> Dict:
        """构建选题卡片"""
        elements = []
        
        for idx, topic in enumerate(topics):
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{idx + 1}. {topic['title']}**\n{topic['description']}"
                }
            })
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "开始写作"
                    },
                    "type": "primary",
                    "value": json.dumps({
                        "topic_id": idx,
                        "title": topic["title"],
                        "description": topic["description"],
                        "keywords": topic.get("keywords", []),
                        "sources": topic.get("sources", [])
                    })
                }]
            })
            
            if idx < len(topics) - 1:
                elements.append({"tag": "hr"})
        
        return {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📝 博客文章选题"
                },
                "template": "blue"
            },
            "elements": elements
        }
    
    def build_article_card(self, title: str, content: str) -> Dict:
        """构建文章卡片"""
        return {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"✅ {title}"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content[:4000]  # 飞书卡片内容限制
                    }
                }
            ]
        }
    
    def build_progress_card(self, title: str, status: str) -> Dict:
        """构建进度卡片"""
        return {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"⏳ {title}"
                },
                "template": "yellow"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": status
                    }
                }
            ]
        }

    def send_digest_to_webhook(
        self, webhook_url: str, articles: List[Dict], topics: List[Dict], date_str: str
    ) -> bool:
        """推送 digest 到飞书 webhook，根据 URL 自动选择：自定义机器人 / Flow"""
        url = webhook_url.strip()
        if url.startswith(FEISHU_WEBHOOK_PREFIX_BOT):
            return self._send_digest_bot(url, articles, topics, date_str)
        if url.startswith(FEISHU_WEBHOOK_PREFIX_FLOW):
            return self._send_digest_flow(url, articles, topics, date_str)
        logger.warning("[feishu] 未知 webhook 格式: %s", url[:60])
        return False

    def _article_display_title(self, a: Dict) -> str:
        title = a.get("title", "")
        title_zh = a.get("title_zh") or ""
        if title_zh.strip() and title_zh != title:
            return f"{title_zh} ({title})"
        return title

    def _send_digest_bot(
        self, webhook_url: str, articles: List[Dict], topics: List[Dict], date_str: str
    ) -> bool:
        """自定义机器人：post 富文本，加粗与分区"""
        content_lines = []
        content_lines.append([{"tag": "text", "text": "📰 今日文章\n"}])
        for a in articles:
            disp = self._article_display_title(a)
            content_lines.append([
                {"tag": "a", "text": disp, "href": a.get("url", "")},
                {"tag": "text", "text": f" · {a.get('source', '')}\n"}
            ])
        content_lines.append([{"tag": "text", "text": "\n💡 AI 选题建议\n"}])
        for t in topics:
            content_lines.append([{"tag": "text", "text": f"【{t.get('title', '')}】\n"}])
            content_lines.append([{"tag": "text", "text": f"  {t.get('reason', '')}\n"}])
            refs = t.get("relatedArticles") or []
            if refs:
                content_lines.append([{"tag": "text", "text": "  关联文章：\n"}])
                for r in refs[:5]:
                    rt = r.get("title", "") or "链接"
                    url = r.get("url", "")
                    if url:
                        content_lines.append([{"tag": "a", "text": f"· {rt}", "href": url}, {"tag": "text", "text": "\n"}])
                    else:
                        content_lines.append([{"tag": "text", "text": f"    · {rt}\n"}])
        content_lines.append([{"tag": "text", "text": "\n— 由 OpenJarvis 自动推送"}])
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"OpenJarvis 每日推送 · {date_str}",
                        "content": content_lines
                    }
                }
            }
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(webhook_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") != 0:
                        logger.warning("[feishu] bot webhook 返回错误: %s", data)
                        return False
                    return True
                logger.warning("[feishu] bot webhook 请求失败: %d %s", resp.status_code, resp.text[:200])
                return False
        except Exception as e:
            logger.error("[feishu] bot webhook 发送异常: %s", e)
            return False

    def _send_digest_flow(
        self, webhook_url: str, articles: List[Dict], topics: List[Dict], date_str: str
    ) -> bool:
        """Flow webhook：content 纯文本，用符号和留白提升可读性"""
        sep = "━━━━━━━━━━━━━━━━━━"
        lines = [
            f"📰 今日文章 · {date_str}",
            sep,
            "",
        ]
        for i, a in enumerate(articles, 1):
            disp = self._article_display_title(a)
            lines.append(f"  {i}. {disp}")
            lines.append(f"     {a.get('url', '')} · {a.get('source', '')}")
            lines.append("")
        lines.extend([sep, "💡 AI 选题建议", sep, ""])
        for t in topics:
            lines.append(f"**【{t.get('title', '')}】**")
            lines.append(f"  {t.get('reason', '')}")
            refs = t.get("relatedArticles") or []
            if refs:
                lines.append("  关联文章：")
                for r in refs[:5]:
                    rt = r.get("title", "") or "链接"
                    url = r.get("url", "")
                    lines.append(f"    · {rt}")
                    if url:
                        lines.append(f"      {url}")
            lines.append("")
        lines.extend([sep, "由 OpenJarvis 自动推送"])
        payload = {
            "title": f"OpenJarvis 每日推送 · {date_str}",
            "content": "\n".join(lines),
            "articles": articles,
            "topics": topics,
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(webhook_url, json=payload)
                if 200 <= resp.status_code < 300:
                    return True
                logger.warning("[feishu] flow webhook 请求失败: %d %s", resp.status_code, resp.text[:200])
                return False
        except Exception as e:
            logger.error("[feishu] flow webhook 发送异常: %s", e)
            return False


feishu_service = FeishuService()

