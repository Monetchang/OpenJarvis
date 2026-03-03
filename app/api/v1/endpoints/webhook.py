from fastapi import APIRouter, Request, BackgroundTasks
from app.core.config import settings
from app.models.schemas import FeishuEventChallenge, TopicInfo
from app.services.feishu import feishu_service
from app.services.agent import agent_service
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/event")
async def handle_event(request: Request):
    """处理飞书事件回调"""
    data = await request.json()
    
    # URL验证
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # 处理其他事件
    event_type = data.get("header", {}).get("event_type")
    logger.info(f"Received event: {event_type}")
    
    return {"code": 0}


@router.post("/card")
async def handle_card_action(request: Request, background_tasks: BackgroundTasks):
    """处理飞书卡片交互回调"""
    data = await request.json()
    
    # 验证token
    if not settings.feishu_verification_token:
        return {"code": 500, "msg": "Feishu verification token not configured"}
    if data.get("token") != settings.feishu_verification_token:
        return {"code": 403, "msg": "Invalid token"}
    
    # 获取操作信息
    action = data.get("action", {})
    value = action.get("value", {})
    
    # 解析选题信息
    try:
        topic_data = json.loads(value) if isinstance(value, str) else value
        topic = TopicInfo(**topic_data)
    except Exception as e:
        logger.error(f"Failed to parse topic: {e}")
        return {"code": 400, "msg": "Invalid topic data"}
    
    # 获取会话信息
    open_chat_id = data.get("open_chat_id")
    open_message_id = data.get("open_message_id")
    card_token = data.get("token")
    
    # 立即返回处理中状态
    progress_card = feishu_service.build_progress_card(
        topic.title,
        "正在生成文章，请稍候..."
    )
    
    # 更新卡片
    await feishu_service.update_card(card_token, progress_card)
    
    # 后台异步生成文章
    background_tasks.add_task(
        generate_and_send_article,
        open_chat_id,
        topic,
        card_token
    )
    
    return {"code": 0}


async def generate_and_send_article(chat_id: str, topic: TopicInfo, card_token: str):
    """生成并发送文章"""
    try:
        # 调用 Agent 生成文章
        article_content = await agent_service.generate_article(topic)
        
        # 构建文章卡片
        article_card = feishu_service.build_article_card(
            topic.title,
            article_content
        )
        
        # 更新卡片为完成状态
        await feishu_service.update_card(card_token, article_card)
        
        # 同时发送完整文章（文本消息）
        await feishu_service.send_message(
            chat_id,
            "text",
            {"text": f"📝 {topic.title}\n\n{article_content}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to generate article: {e}")
        
        # 更新为错误状态
        error_card = feishu_service.build_progress_card(
            topic.title,
            f"生成失败：{str(e)}"
        )
        await feishu_service.update_card(card_token, error_card)

