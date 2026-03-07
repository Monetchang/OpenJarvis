# coding=utf-8
"""
文章 Pydantic 模式
"""
from typing import Optional
from pydantic import BaseModel


class ArticleResponse(BaseModel):
    """文章响应"""
    id: int
    title: str
    titleZh: Optional[str] = None
    source: str
    feedName: str
    summary: str
    url: str
    publishedAt: str
    pushedAt: str
    isRead: bool

    class Config:
        from_attributes = True

