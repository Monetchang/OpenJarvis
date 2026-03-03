import httpx
import json
import time
from typing import Optional, Dict, Any, List
from app.core.config import settings


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


feishu_service = FeishuService()

