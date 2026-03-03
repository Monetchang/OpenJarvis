# coding=utf-8
"""
文章过滤 Pydantic 模式
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DomainResponse(BaseModel):
    """领域响应"""
    id: int
    name: str
    description: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DomainCreateRequest(BaseModel):
    """创建领域请求"""
    name: str
    description: Optional[str] = None
    enabled: bool = True


class DomainUpdateRequest(BaseModel):
    """更新领域请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: int
    domain_id: int
    keyword_type: str
    keyword_text: str
    is_regex: bool
    is_required: bool
    alias: Optional[str]
    priority: int
    max_results: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class KeywordCreateRequest(BaseModel):
    """创建关键词请求"""
    domain_id: int
    keyword_type: str = "positive"  # positive/negative
    keyword_text: str
    is_regex: bool = False
    is_required: bool = False
    alias: Optional[str] = None
    priority: int = 0
    max_results: Optional[int] = None


class FilterRequest(BaseModel):
    """过滤请求参数"""
    domain_id: Optional[int] = None
    keywords: Optional[List[str]] = None  # 正向关键词列表
    exclude_keywords: Optional[List[str]] = None  # 负向关键词列表

