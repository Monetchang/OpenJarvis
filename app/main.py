# coding=utf-8
"""
主应用入口
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1 import api_router
from app.core.logging_middleware import RequestLoggingMiddleware
from app.core.exception_handler import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.core.database import get_db_context, engine
from app.core.config import settings
from app.models.config import AppConfig
from app.models.subscriber import EmailSubscriber
from app.services import scheduler_service
from app.orchestration import create_tables
from app.orchestration.graphs.definitions import build_blog_graph
from app.orchestration.ws import EventBroadcaster
from app.orchestration.ws.routes import router as ws_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ws_broadcaster = EventBroadcaster()
    app.state._loop = asyncio.get_running_loop()
    EmailSubscriber.__table__.create(engine, checkfirst=True)
    create_tables(engine)
    build_blog_graph()
    with get_db_context() as db:
        cfg = db.query(AppConfig).filter(AppConfig.key == "rss_schedule").first()
        if cfg and cfg.value:
            try:
                cron = json.loads(cfg.value)
            except (json.JSONDecodeError, TypeError):
                cron = cfg.value
        else:
            cron = settings.RSS_SCHEDULE
    scheduler_service.init_scheduler(cron)
    yield
    scheduler_service.shutdown()


app = FastAPI(
    title="OpenJarvis Backend",
    description="智能写作工作台后端服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "status": "ok",
        "service": "OpenJarvis Backend",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "OpenJarvis Backend"
    }
