# coding=utf-8
"""
通用响应模式
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True

