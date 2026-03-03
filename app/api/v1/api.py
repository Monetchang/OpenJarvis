# coding=utf-8
"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1.endpoints import feed, article, ai, webhook, filter, config, subscribe, user
from app.orchestration.api import router as orchestration_router

api_router = APIRouter()

api_router.include_router(feed.router, prefix="/feed", tags=["RSS订阅源"])
api_router.include_router(subscribe.router, prefix="/subscribe", tags=["邮件订阅"])
api_router.include_router(user.router, prefix="/user", tags=["用户"])
api_router.include_router(article.router, prefix="/article", tags=["文章推送"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI功能"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
api_router.include_router(filter.router, prefix="/filter", tags=["文章过滤"])
api_router.include_router(config.router, prefix="/config", tags=["全局配置"])
api_router.include_router(orchestration_router, tags=["Orchestration"])

