"""
示例：如何使用 OpenJarvis 推送选题卡片到飞书群组
"""
import asyncio
import httpx


async def send_topic_card_example():
    """发送选题卡片示例"""
    
    # 选题数据
    topics = [
        {
            "title": "Python 异步编程最佳实践",
            "description": "深入探讨 asyncio、事件循环和并发模式",
            "keywords": ["Python", "异步", "asyncio"],
            "sources": ["https://docs.python.org/3/library/asyncio.html"]
        },
        {
            "title": "微服务架构中的分布式追踪",
            "description": "使用 OpenTelemetry 实现全链路追踪",
            "keywords": ["微服务", "分布式追踪", "OpenTelemetry"],
            "sources": ["https://opentelemetry.io/"]
        }
    ]
    
    # 构建卡片
    from app.services.feishu import feishu_service
    card = feishu_service.build_topic_card(topics)
    
    # 发送到群组
    chat_id = "your_chat_id"  # 替换为实际的群组 ID
    
    result = await feishu_service.send_message(
        chat_id,
        "interactive",
        card
    )
    
    print(f"发送结果: {result}")


if __name__ == "__main__":
    asyncio.run(send_topic_card_example())

