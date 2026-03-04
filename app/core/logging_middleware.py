# coding=utf-8
"""
请求日志中间件

注：BaseHTTPMiddleware 在读取 request.body 后会破坏 ASGI receive 流，
导致 listen_for_disconnect 收到 http.request 而崩溃，故不读取 body。
"""
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        logger.info(
            "请求: %s %s",
            request.method,
            request.url.path,
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )
        try:
            response = await call_next(request)
            logger.info(
                "响应: %s %s - %d",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": f"{time.time() - start_time:.3f}s",
                },
            )
            return response
        except Exception as e:
            logger.error(
                "请求异常: %s %s - %s",
                request.method,
                request.url.path,
                str(e),
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "process_time": f"{time.time() - start_time:.3f}s",
                },
            )
            raise

