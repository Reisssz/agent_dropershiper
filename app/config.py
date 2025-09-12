import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./pet_agent.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # APIs
    TIKTOK_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None  # Para Whisper API
    
    # Social Media Credentials
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Diretórios
    BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))
    VIDEOS_RAW_DIR: str = "videos/raw"
    VIDEOS_PROCESSED_DIR: str = "videos/processed"
    VIDEOS_READY_DIR: str = "videos/ready"
    
    # Configurações de processamento
    MAX_VIDEO_DURATION: int = 60  # segundos
    TARGET_RESOLUTION: str = "1080x1920"  # 9:16 para Stories/Reels
    
    class Config:
        env_file = ".env"

settings = Settings()