# coding=utf-8
"""
AI 功能 Pydantic 模式
"""
from pydantic import BaseModel, validator, Field, ConfigDict
from typing import List, Optional


class RelatedArticle(BaseModel):
    """相关文章"""
    title: str
    source: str
    url: str


class IdeaGenerateRequest(BaseModel):
    """生成选题请求。请求体支持 articleIds 或 article_ids，count 需在 3-10。"""
    articleIds: Optional[List[int]] = Field(None, alias="article_ids")
    count: int = Field(5, ge=3, le=10, description="生成数量 3-10")

    model_config = ConfigDict(populate_by_name=True)

    @validator("count")
    def validate_count(cls, v):
        if not 3 <= v <= 10:
            raise ValueError("生成数量必须在3-10之间")
        return v


class IdeaResponse(BaseModel):
    """选题响应"""
    id: str
    title: str
    relatedArticles: List[RelatedArticle]
    reason: str


class ArticleGenerateRequest(BaseModel):
    """生成文章请求"""
    ideaId: str
    ideaTitle: str
    style: str
    audience: str
    length: str = "medium"
    language: str = "zh-CN"
    mode: str = "pro"  # pro=LangGraph 计划驱动, quick=单次 prompt


class ArticleGenerateResponse(BaseModel):
    """生成文章响应"""
    articleId: str
    title: str
    content: str
    wordCount: int
    generatedAt: str

