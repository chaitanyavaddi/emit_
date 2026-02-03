from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/test_user_pool",
        description="PostgreSQL database URL"
    )
    db_pool_size: int = Field(default=10, ge=1, le=50)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_pool_pre_ping: bool = Field(default=True)
    
    # User Pool Settings
    default_max_retries: int = Field(default=10, ge=1, le=50)
    max_retry_wait_seconds: int = Field(default=10, ge=1, le=60)
    min_backoff_seconds: float = Field(default=0.5, ge=0.1, le=5.0)
    max_backoff_seconds: float = Field(default=2.0, ge=0.5, le=10.0)
    
    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1000, le=65535)
    api_reload: bool = Field(default=False)
    api_workers: int = Field(default=1, ge=1, le=8)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # CORS
    allowed_origins: str = Field(default="*")
    
    # Application
    app_name: str = Field(default="Test User Pool API")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    @field_validator('allowed_origins')
    @classmethod
    def parse_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins into list"""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v.startswith(('postgresql://', 'postgresql+psycopg2://', 'postgresql+asyncpg://')):
            raise ValueError('Database URL must start with postgresql://')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()