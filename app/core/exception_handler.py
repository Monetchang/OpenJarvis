# coding=utf-8
"""
全局异常处理器
"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg"),
            "type": error.get("type")
        })
    
    logger.error(
        f"请求验证失败: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "errors": error_details,
            "body": exc.body if hasattr(exc, 'body') else None,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "data": {
                "errors": error_details
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理 HTTP 异常"""
    logger.warning(
        f"HTTP异常: {request.method} {request.url.path} - {exc.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": exc.detail,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail if isinstance(exc.detail, str) else "请求失败",
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    error_traceback = traceback.format_exc()
    
    logger.error(
        f"未处理的异常: {request.method} {request.url.path}",
        exc_info=True,
        extra={
            "method": request.method,
            "path": request.url.path,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": error_traceback,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None
        }
    )

