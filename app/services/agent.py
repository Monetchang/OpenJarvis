from openai import AsyncOpenAI
from app.config import settings
from app.models.schemas import TopicInfo
from typing import List


class AgentService:
    def __init__(self):
        if settings.llm_provider == "deepseek":
            self.client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url
            )
            self.model = settings.deepseek_model
        else:
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            self.model = settings.openai_model
    
    async def generate_article(self, topic: TopicInfo) -> str:
        """根据选题生成文章"""
        prompt = self._build_prompt(topic)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的技术博客作者，擅长撰写深入浅出、结构清晰的技术文章。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def _build_prompt(self, topic: TopicInfo) -> str:
        """构建生成文章的 Prompt"""
        prompt = f"""请根据以下信息撰写一篇技术博客文章：

标题：{topic.title}

描述：{topic.description}

关键词：{', '.join(topic.keywords)}
"""
        
        if topic.sources:
            prompt += f"\n参考资料：\n"
            for source in topic.sources:
                prompt += f"- {source}\n"
        
        prompt += """

要求：
1. 文章结构清晰，包含引言、正文、总结
2. 使用 Markdown 格式
3. 内容深入浅出，适合技术读者
4. 包含代码示例（如适用）
5. 字数控制在 2000-3000 字
"""
        
        return prompt


agent_service = AgentService()

