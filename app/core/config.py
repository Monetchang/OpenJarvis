# coding=utf-8
"""
应用配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_APP_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_APP_ROOT / ".env")


class Settings(BaseSettings):
    # 数据库配置
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "rss_ai_service"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    
    # AI 配置
    AI_API_KEY: str = ""
    AI_MODEL: str = "deepseek/deepseek-chat"
    AI_API_BASE: str = ""
    AI_TEMPERATURE: float = 1.0
    AI_MAX_TOKENS: int = 5000
    AI_TIMEOUT: int = 120
    
    # LLM 配置兼容性
    @property
    def llm_provider(self):
        """LLM 提供商（从 AI_MODEL 提取）"""
        if "/" in self.AI_MODEL:
            return self.AI_MODEL.split("/")[0]
        return "openai"
    
    @property
    def llm_model(self):
        """LLM 模型名称"""
        if "/" in self.AI_MODEL:
            return self.AI_MODEL.split("/")[1]
        return self.AI_MODEL
    
    @property
    def llm_api_key(self):
        return self.AI_API_KEY
    
    @property
    def llm_api_base(self):
        return self.AI_API_BASE if self.AI_API_BASE else None
    
    @property
    def llm_temperature(self):
        return self.AI_TEMPERATURE
    
    @property
    def llm_max_tokens(self):
        return self.AI_MAX_TOKENS
    
    # 翻译配置（mt=免费机器翻译, ai=LLM翻译）
    TRANSLATION_PROVIDER: str = "ai"
    TRANSLATION_ENABLED: bool = True
    TRANSLATION_LANGUAGE: str = "Chinese"
    
    # 选题配置
    TOPICS_ENABLED: bool = True
    AI_ARTICLE_PROMPT_MODULE: str = "ai_article_prompt"
    TOPICS_MIN_COUNT: int = 3
    TOPICS_MAX_COUNT: int = 10
    
    # RSS 配置
    RSS_TIMEOUT: int = 10
    RSS_CONNECT_TIMEOUT: int = 10
    RSS_REQUEST_INTERVAL: int = 2000
    RSS_MAX_CONCURRENT: int = 8
    RSS_USE_PROXY: bool = False
    RSS_PROXY_URL: str = ""
    RSS_PROXY_HTTPS_URL: str = ""        # 仅覆盖 https 代理，留空则与 RSS_PROXY_URL 相同
    RSS_NO_PROXY: str = ""               # 不走代理的域名，逗号分隔
    RSS_HTTP_CONNECT_TIMEOUT: int = 10
    RSS_HTTP_READ_TIMEOUT: int = 10
    RSS_HTTP_RETRIES: int = 1
    TIMEZONE: str = "Asia/Shanghai"
    RSS_SCHEDULE: str = "0 9 * * *"  # 全局 RSS 抓取定时（cron 表达式），所有源共享
    
    # 推送测试模式（仅抓 1 个源、跳过选题，节省时间）
    PUSH_TEST_MODE: bool = False

    # 邮件推送（二选一：Resend 仅需 API Key，SMTP 需完整配置）
    RESEND_API_KEY: str = ""  # 设置后优先使用，无需配置 SMTP
    RESEND_FROM: str = "OpenJarvis <onboarding@resend.dev>"  # 测试可用该地址
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    # 用户/邀请码
    INVITE_CODES: str = "DEMO2024,TEST2024"  # 逗号分隔，大小写敏感
    SUBSCRIBER_COOKIE_NAME: str = "subscriber_email"
    SUBSCRIBER_COOKIE_MAX_AGE: int = 365 * 24 * 3600  # 1年

    # Feishu 配置（可选）
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_ENCRYPT_KEY: str = ""
    
    # 兼容性别名
    @property
    def feishu_app_id(self):
        return self.FEISHU_APP_ID
    
    @property
    def feishu_app_secret(self):
        return self.FEISHU_APP_SECRET
    
    @property
    def feishu_verification_token(self):
        return self.FEISHU_VERIFICATION_TOKEN
    
    @property
    def feishu_encrypt_key(self):
        return self.FEISHU_ENCRYPT_KEY
    
    # 开发环境（ENV=DEV 时启用 mock-events 等）
    ENV: str = "production"

    # 编排：False=默认 GRAPH_RUN（LangGraph），True=旧多 stage 推进（stage_a->stage_b->stage_c）用于回滚
    ORCHESTRATION_USE_LEGACY_STAGE_FLOW: bool = False

    class Config:
        case_sensitive = True


settings = Settings()
