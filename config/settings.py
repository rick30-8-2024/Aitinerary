"""Settings configuration using pydantic-settings for environment variable management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
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
    
    YOUTUBE_PROXIES: str = ""
    YOUTUBE_PROXY_TIMEOUT: int = 10
    YOUTUBE_MAX_RETRIES: int = 5
    
    USE_FREE_PROXIES: bool = True
    FREE_PROXY_REFRESH_INTERVAL: int = 600
    FREE_PROXY_MIN_POOL_SIZE: int = 10
    FREE_PROXY_TIMEOUT_MS: int = 5000
    FREE_PROXY_ANONYMITY: str = "elite,anonymous"
    REQUEST_DELAY_MIN: float = 1.0
    REQUEST_DELAY_MAX: float = 3.0
    
    APP_NAME: str = "Aitinerary"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @field_validator("YOUTUBE_PROXIES", mode="before")
    @classmethod
    def validate_proxies(cls, v):
        """Validate and clean proxy string."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    def get_proxy_list(self) -> list[str]:
        """
        Parse comma-separated proxy URLs into a list.
        
        Returns:
            List of proxy URLs (e.g., ['http://proxy1:8080', 'http://user:pass@proxy2:8080'])
        """
        if not self.YOUTUBE_PROXIES:
            return []
        return [p.strip() for p in self.YOUTUBE_PROXIES.split(",") if p.strip()]


settings = Settings()
