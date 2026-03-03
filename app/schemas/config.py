# coding=utf-8
"""
配置管理 Pydantic 模式
"""
from pydantic import BaseModel, validator
from typing import Optional
from croniter import croniter


class ConfigResponse(BaseModel):
    """配置响应"""
    rssSchedule: str
    translationEnabled: bool
    
    class Config:
        from_attributes = True


class ConfigUpdateRequest(BaseModel):
    """更新配置请求"""
    rssSchedule: Optional[str] = None
    translationEnabled: Optional[bool] = None
    
    @validator("rssSchedule")
    def validate_schedule(cls, v):
        if v is not None:
            try:
                croniter(v)
            except Exception:
                raise ValueError("cron 表达式格式错误")
        return v

