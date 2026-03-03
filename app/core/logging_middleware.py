# coding=utf-8
"""
请求日志中间件
"""
import json
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        start_time = time.time()
        
        # 读取请求体（需要重新创建请求以支持重复读取）
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        body = json.loads(body_bytes.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body = body_bytes.decode('utf-8', errors='replace')[:500]  # 限制长度
                
                # 重新创建请求以支持后续处理
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                
                request._receive = receive
            except Exception as e:
                body = f"<无法读取请求体: {str(e)}>"
        
        # 记录请求信息
        logger.info(
            f"请求: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "body": body,
                "client": request.client.host if request.client else None,
            }
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"响应: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s",
                }
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"请求异常: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "body": body,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": f"{process_time:.3f}s",
                }
            )
            raise

