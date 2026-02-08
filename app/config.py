from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_encrypt_key: str = ""
    feishu_webhook_url: str
    
    llm_provider: Literal["openai", "deepseek"] = "openai"
    
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    
    class Config:
        env_file = ".env"


settings = Settings()

