from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class FeishuEventChallenge(BaseModel):
    challenge: str
    token: str
    type: str


class FeishuCardAction(BaseModel):
    open_id: str
    user_id: str
    open_message_id: str
    open_chat_id: str
    tenant_key: str
    token: str
    action: Dict[str, Any]


class TopicInfo(BaseModel):
    title: str
    description: str
    keywords: List[str]
    sources: Optional[List[str]] = []

