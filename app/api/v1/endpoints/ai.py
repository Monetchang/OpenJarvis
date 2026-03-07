# coding=utf-8
"""
AI 灵感选题和文章生成路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.article import RSSItem
from app.models.ai import BlogTopic, TopicReference
from app.services.ai_service import get_ai_service
from app.schemas.ai import IdeaGenerateRequest, IdeaResponse, ArticleGenerateRequest, ArticleGenerateResponse, RelatedArticle
from app.schemas.common import ResponseModel

logger = logging.getLogger(__name__)
router = APIRouter()


def _ref_with_title_zh(db: Session, ref: TopicReference) -> dict:
    """为参考文章附加 titleZh（按 url 查 RSSItem）。"""
    item = db.query(RSSItem).filter(RSSItem.url == ref.article_url).first()
    return {
        "title": ref.article_title,
        "titleZh": getattr(item, "title_zh", None) if item else None,
        "source": ref.source or "",
        "url": ref.article_url,
    }


@router.get("/ideas")
def get_today_ideas(db: Session = Depends(get_db)):
    """从存储中获取当日选题数据。"""
    today = datetime.now().strftime("%Y-%m-%d")
    topics = db.query(BlogTopic).filter(BlogTopic.date == today).order_by(BlogTopic.id).all()
    ideas = []
    for t in topics:
        refs = db.query(TopicReference).filter(TopicReference.topic_id == t.id).all()
        ideas.append({
            "id": f"idea_{t.id}",
            "title": t.title,
            "relatedArticles": [_ref_with_title_zh(db, r) for r in refs],
            "reason": t.description
        })
    return {"code": 0, "message": "success", "data": {"ideas": ideas}}


@router.post("/generate-ideas")
def generate_ideas(
    request: Optional[IdeaGenerateRequest] = Body(None),
    db: Session = Depends(get_db)
):
    """生成选题。先清除存储中当日选题，再生成并重新存储。"""
    if request is None:
        request = IdeaGenerateRequest()
    try:
        logger.info(
            f"生成选题请求",
            extra={
                "count": request.count,
                "articleIds": request.articleIds,
            }
        )
        today = datetime.now().strftime("%Y-%m-%d")
        db.query(BlogTopic).filter(BlogTopic.date == today).delete()

        # 获取 RSS 条目
        query = db.query(RSSItem)
        
        if request.articleIds:
            query = query.filter(RSSItem.id.in_(request.articleIds))
        else:
            # 获取最新的文章
            query = query.order_by(RSSItem.created_at.desc()).limit(100)
        
        articles = query.all()
        
        if not articles:
            logger.warning("没有足够的文章数据生成选题")
            raise HTTPException(status_code=400, detail="没有足够的文章数据生成选题")
        
        # 转换为字典格式
        rss_items = []
        for article in articles:
            item = {
                "title": article.title,
                "feed_id": article.feed_id,
                "url": article.url,
                "published_at": article.published_at or "",
                "summary": article.summary or "",
                "author": article.author or "",
                "crawl_time": article.last_crawl_time or ""
            }
            rss_items.append(item)
        
        # 调用服务生成选题
        service = get_ai_service()
        result = service.generate_topics(rss_items)
        
        if not result.success:
            logger.error(f"AI服务生成选题失败: {result.error}")
            raise HTTPException(status_code=500, detail=result.error or "AI服务暂时不可用")
        
        topics = result.topics
        
        if not topics:
            logger.error("AI服务返回空选题列表")
            raise HTTPException(status_code=500, detail="AI服务暂时不可用")
        
        # 保存到数据库
        now = datetime.now()
        crawl_time = now.strftime("%H:%M")
        
        result_ideas = []
        
        for topic in topics[:request.count]:
            # 保存选题
            db_topic = BlogTopic(
                title=topic.title,
                description=topic.description,
                date=today,
                crawl_time=crawl_time,
                news_count=len(articles)
            )
            db.add(db_topic)
            db.flush()
            
            # 关联文章：保存到 TopicReference，供生成文章时使用
            raw_refs = getattr(topic, "related_articles", None) or []
            related_articles = []
            for r in raw_refs:
                if isinstance(r, dict) and (r.get("title") or r.get("url")):
                    ref = TopicReference(
                        topic_id=db_topic.id,
                        article_title=r.get("title", ""),
                        article_url=r.get("url", ""),
                        source=r.get("source", "参考文章")
                    )
                    db.add(ref)
                    item = db.query(RSSItem).filter(RSSItem.url == ref.article_url).first()
                    title_zh = getattr(item, "title_zh", None) if item else None
                    related_articles.append({
                        "title": ref.article_title,
                        "titleZh": title_zh,
                        "source": ref.source,
                        "url": ref.article_url
                    })

            result_ideas.append({
                "id": f"idea_{db_topic.id}",
                "title": topic.title,
                "relatedArticles": related_articles,
                "reason": topic.description
            })
        
        db.commit()
        
        logger.info(f"选题生成成功: count={len(result_ideas)}")
        
        return {
            "code": 0,
            "message": "生成成功",
            "data": {"ideas": result_ideas}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成选题异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成选题失败: {str(e)}")


@router.post("/generate-article")
def generate_article(
    request: ArticleGenerateRequest,
    db: Session = Depends(get_db)
):
    """生成文章"""
    try:
        logger.info(
            f"生成文章请求",
            extra={
                "ideaId": request.ideaId,
                "ideaTitle": request.ideaTitle,
                "style": request.style,
                "audience": request.audience,
                "length": request.length,
                "language": request.language,
            }
        )
        
        # 根据 ideaId 获取选题的参考文章
        related_articles = []
        if request.ideaId and request.ideaId.startswith("idea_"):
            try:
                topic_id = int(request.ideaId.replace("idea_", ""))
                refs = db.query(TopicReference).filter(TopicReference.topic_id == topic_id).all()
                related_articles = [{"title": r.article_title, "url": r.article_url, "source": r.source or ""} for r in refs]
            except (ValueError, Exception):
                pass

        service = get_ai_service()
        content = service.generate_article(
            title=request.ideaTitle,
            style=request.style,
            audience=request.audience,
            length=request.length or "medium",
            language=request.language or "zh-CN",
            related_articles=related_articles
        )
        
        if not content:
            logger.error("AI未返回响应内容")
            raise HTTPException(status_code=500, detail="AI未返回响应")
        
        # 统计字数
        word_count = len(content.replace(" ", "").replace("\n", ""))
        
        logger.info(f"文章生成成功: wordCount={word_count}")
        
        return {
            "code": 0,
            "message": "生成成功",
            "data": {
                "articleId": f"gen_article_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "title": request.ideaTitle,
                "content": content,
                "wordCount": word_count,
                "generatedAt": datetime.now().isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成文章异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

