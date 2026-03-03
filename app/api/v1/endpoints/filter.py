# coding=utf-8
"""
文章过滤路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.filter import ArticleDomain, ArticleKeyword
from app.schemas.filter import (
    DomainResponse, DomainCreateRequest, DomainUpdateRequest,
    KeywordResponse, KeywordCreateRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/domains")
def get_domains(
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取领域列表"""
    try:
        query = db.query(ArticleDomain)
        
        if enabled is not None:
            query = query.filter(ArticleDomain.enabled == enabled)
        
        domains = query.order_by(ArticleDomain.id).all()
        
        result = []
        for domain in domains:
            result.append({
                "id": domain.id,
                "name": domain.name,
                "description": domain.description,
                "enabled": domain.enabled,
                "created_at": domain.created_at.isoformat() if domain.created_at else "",
                "updated_at": domain.updated_at.isoformat() if domain.updated_at else ""
            })
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取领域列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取领域列表失败: {str(e)}")


@router.post("/domains")
def create_domain(
    request: DomainCreateRequest,
    db: Session = Depends(get_db)
):
    """创建领域"""
    try:
        logger.info(f"创建领域请求: name={request.name}, description={request.description}")
        
        # 检查名称是否已存在
        existing = db.query(ArticleDomain).filter(ArticleDomain.name == request.name).first()
        if existing:
            logger.warning(f"领域名称已存在: {request.name}")
            raise HTTPException(status_code=400, detail="领域名称已存在")
        
        domain = ArticleDomain(
            name=request.name,
            description=request.description,
            enabled=request.enabled if request.enabled is not None else True
        )
        db.add(domain)
        db.commit()
        db.refresh(domain)
        
        logger.info(f"领域创建成功: id={domain.id}, name={domain.name}")
        
        return {
            "code": 0,
            "message": "创建成功",
            "data": {
                "id": domain.id,
                "name": domain.name,
                "description": domain.description,
                "enabled": domain.enabled,
                "created_at": domain.created_at.isoformat() if domain.created_at else "",
                "updated_at": domain.updated_at.isoformat() if domain.updated_at else ""
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建领域失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建领域失败: {str(e)}")


@router.put("/domains/{domain_id}", response_model=DomainResponse)
def update_domain(
    domain_id: int,
    request: DomainUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新领域"""
    try:
        domain = db.query(ArticleDomain).filter(ArticleDomain.id == domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="领域不存在")
        
        if request.name is not None:
            # 检查名称是否与其他领域冲突
            existing = db.query(ArticleDomain).filter(
                ArticleDomain.name == request.name,
                ArticleDomain.id != domain_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="领域名称已存在")
            domain.name = request.name
        
        if request.description is not None:
            domain.description = request.description
        
        if request.enabled is not None:
            domain.enabled = request.enabled
        
        db.commit()
        db.refresh(domain)
        return domain
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新领域失败: {str(e)}")


@router.delete("/domains/{domain_id}")
def delete_domain(
    domain_id: int,
    db: Session = Depends(get_db)
):
    """删除领域"""
    domain = db.query(ArticleDomain).filter(ArticleDomain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="领域不存在")
    
    db.delete(domain)
    db.commit()
    
    return {
        "code": 0,
        "message": "删除成功",
        "data": {"success": True}
    }


@router.get("/keywords", response_model=List[KeywordResponse])
def get_keywords(
    domain_id: Optional[int] = Query(None),
    keyword_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取关键词列表"""
    query = db.query(ArticleKeyword)
    
    if domain_id is not None:
        query = query.filter(ArticleKeyword.domain_id == domain_id)
    
    if keyword_type is not None:
        query = query.filter(ArticleKeyword.keyword_type == keyword_type)
    
    keywords = query.order_by(
        ArticleKeyword.priority.desc(),
        ArticleKeyword.created_at.desc()
    ).all()
    return keywords


@router.post("/keywords", response_model=KeywordResponse)
def create_keyword(
    request: KeywordCreateRequest,
    db: Session = Depends(get_db)
):
    """创建关键词"""
    try:
        # 检查领域是否存在
        domain = db.query(ArticleDomain).filter(ArticleDomain.id == request.domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="领域不存在")
        
        keyword = ArticleKeyword(
            domain_id=request.domain_id,
            keyword_type=request.keyword_type,
            keyword_text=request.keyword_text,
            is_regex=request.is_regex,
            is_required=request.is_required,
            alias=request.alias,
            priority=request.priority,
            max_results=request.max_results
        )
        db.add(keyword)
        db.commit()
        db.refresh(keyword)
        return keyword
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建关键词失败: {str(e)}")


@router.delete("/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db)
):
    """删除关键词"""
    keyword = db.query(ArticleKeyword).filter(ArticleKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    
    db.delete(keyword)
    db.commit()
    
    return {
        "code": 0,
        "message": "删除成功",
        "data": {"success": True}
    }

