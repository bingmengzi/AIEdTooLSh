"""应用配置管理 - 从 .env 文件加载环境变量"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from typing import Optional

# 基础目录
_BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # AI Provider API Keys
    KIMI_API_KEY: str = ""
    QWEN_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # Server Config
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    @property
    def BASE_DIR(self) -> Path:
        return _BASE_DIR
    
    @property
    def PROMPTS_DIR(self) -> Path:
        return _BASE_DIR / "app" / "prompts"
    
    @property
    def OUTPUTS_DIR(self) -> Path:
        outputs = _BASE_DIR / "app" / "storage" / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        return outputs
    
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],  # 先加载backend/.env，再用根目录.env覆盖
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
