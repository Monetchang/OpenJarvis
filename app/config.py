from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_verification_token: Optional[str] = None
    feishu_encrypt_key: str = ""
    feishu_webhook_url: Optional[str] = None
    
    llm_provider: Literal["openai", "deepseek"] = "openai"
    
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

