# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str
    VERSION: str
    ENVIRONMENT: str

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Rate Limiting
    MAX_LOGIN_ATTEMPTS: int
    LOCKOUT_MINUTES: int

    # CORS
    CORS_ORIGINS: str

    USE_MOCK_DATA: bool = True

    # Pydantic v2 Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

# Instantiate the settings object to be used across the app
settings = Settings()