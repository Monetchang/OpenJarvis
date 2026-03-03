# coding=utf-8
"""
RSS 订阅源 Pydantic 模式
"""
from pydantic import BaseModel, validator
from typing import Optional
from croniter import croniter


class FeedCreate(BaseModel):
    """创建订阅源请求"""
    name: str
    url: str
    pushCount: int = 10
    isTrusted: bool = False

    @validator("pushCount")
    def validate_push_count(cls, v):
        if not 1 <= v <= 50:
            raise ValueError("推送数量必须在1-50之间")
        return v


class FeedUpdate(BaseModel):
    """更新订阅源请求"""
    name: Optional[str] = None
    url: Optional[str] = None
    pushCount: Optional[int] = None
    isTrusted: Optional[bool] = None

    @validator("pushCount")
    def validate_push_count(cls, v):
        if v is not None and not 1 <= v <= 50:
            raise ValueError("推送数量必须在1-50之间")
        return v


class FeedResponse(BaseModel):
    """订阅源响应"""
    id: str
    name: str
    url: str
    pushCount: int
    isTrusted: bool
    createdAt: str

    class Config:
        from_attributes = True

