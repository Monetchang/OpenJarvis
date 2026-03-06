# coding=utf-8
"""用户模块 Schema"""
from pydantic import BaseModel, EmailStr, Field


class SubscribeRequest(BaseModel):
    email: EmailStr
    inviteCode: str = Field(..., alias="inviteCode")

    model_config = {"populate_by_name": True}


class FeishuSubscribeRequest(BaseModel):
    webhook_url: str
    inviteCode: str = Field(..., alias="inviteCode")

    model_config = {"populate_by_name": True}


class SubscribeResponse(BaseModel):
    success: bool


class UserMeResponse(BaseModel):
    email: str | None
    isEmailBound: bool


class UnbindResponse(BaseModel):
    success: bool
