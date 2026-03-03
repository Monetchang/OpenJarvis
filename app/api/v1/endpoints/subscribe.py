# coding=utf-8
"""
邮件订阅路由（1.1 邮箱注册/绑定）
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.subscriber import EmailSubscriber
from app.schemas.user import SubscribeRequest
from app.services.scheduler_service import run_digest_job

router = APIRouter()
logger = logging.getLogger(__name__)

_VALID_CODES = {c.strip() for c in settings.INVITE_CODES.split(",") if c.strip()}


def _check_invite_code(code: str) -> bool:
    return code.strip() in _VALID_CODES


@router.post("/email")
def subscribe_email(
    req: SubscribeRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """1.1 邮箱注册/绑定（提交邮箱+邀请码，绑定后用于每日推送）"""
    if not _check_invite_code(req.inviteCode):
        raise HTTPException(status_code=400, detail="邀请码错误")
    email = req.email.lower().strip()
    existing = db.query(EmailSubscriber).filter(EmailSubscriber.email == email).first()
    if existing:
        if existing.is_active:
            response.set_cookie(
                key=settings.SUBSCRIBER_COOKIE_NAME,
                value=email,
                httponly=True,
                samesite="lax",
                max_age=settings.SUBSCRIBER_COOKIE_MAX_AGE,
            )
            return {"code": 0, "message": "绑定成功", "data": {"success": True}}
        existing.is_active = 1
        db.commit()
    else:
        sub = EmailSubscriber(email=email)
        db.add(sub)
        db.commit()
    response.set_cookie(
        key=settings.SUBSCRIBER_COOKIE_NAME,
        value=email,
        httponly=True,
        samesite="lax",
        max_age=settings.SUBSCRIBER_COOKIE_MAX_AGE,
    )
    return {"code": 0, "message": "绑定成功", "data": {"success": True}}


def _run_trigger_push():
    result = run_digest_job(force_fetch=True, skip_when_no_fetch=False)
    logger.info("[trigger-push] 完成: %s", result)


@router.post("/trigger-push")
def trigger_email_push(background_tasks: BackgroundTasks):
    """主动触发一次：抓取 -> 生成选题 -> 推送到所有订阅邮箱（后台执行，立即返回）"""
    background_tasks.add_task(_run_trigger_push)
    return {"code": 0, "message": "推送任务已启动，请稍后查收邮件", "data": {"status": "running"}}


@router.delete("/email/{email_id}")
def unsubscribe_email(email_id: int, db: Session = Depends(get_db)):
    """取消订阅"""
    sub = db.query(EmailSubscriber).filter(EmailSubscriber.id == email_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    sub.is_active = 0
    db.commit()
    return {"code": 0, "message": "已取消订阅"}
