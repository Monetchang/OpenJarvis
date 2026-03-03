# coding=utf-8
"""
用户模块（1.2 获取绑定状态 / 1.3 解绑）
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.subscriber import EmailSubscriber

router = APIRouter()


@router.get("/me")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """1.2 获取当前用户/绑定状态"""
    email = request.cookies.get(settings.SUBSCRIBER_COOKIE_NAME)
    if not email:
        return {"code": 0, "message": "success", "data": {"email": None, "isEmailBound": False}}
    sub = db.query(EmailSubscriber).filter(
        EmailSubscriber.email == email,
        EmailSubscriber.is_active == 1,
    ).first()
    if not sub:
        return {"code": 0, "message": "success", "data": {"email": None, "isEmailBound": False}}
    return {"code": 0, "message": "success", "data": {"email": sub.email, "isEmailBound": True}}


@router.post("/unbind")
def unbind_email(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """1.3 解绑邮箱"""
    email = request.cookies.get(settings.SUBSCRIBER_COOKIE_NAME)
    if not email:
        raise HTTPException(status_code=404, detail="未绑定邮箱")
    sub = db.query(EmailSubscriber).filter(EmailSubscriber.email == email).first()
    if sub:
        sub.is_active = 0
        db.commit()
    response.delete_cookie(settings.SUBSCRIBER_COOKIE_NAME)
    return {"code": 0, "message": "解绑成功", "data": {"success": True}}
