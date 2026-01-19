"""Settings configuration using pydantic-settings for environment variable management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "aitinerary"
    
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-3-flash-preview"
    
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5760
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    APP_NAME: str = "Aitinerary"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
