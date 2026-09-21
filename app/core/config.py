# app/core/config.py
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str = "AI-Powered GeM Compliance Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Rate Limiting
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 2

    # CORS
    CORS_ORIGINS: str = "*"

    USE_MOCK_DATA: bool = True

    # Project Root & Data Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MOCK_DIR: Path = DATA_DIR / "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def get_mock_file(self, filename: str) -> Path:
        """
        Locates mock JSON files in either data/mock/ or data/mock/government_verification/
        """
        search_locations = [
            self.MOCK_DIR / "government_verification" / filename,
            self.MOCK_DIR / filename,
            Path.cwd() / "data" / "mock" / "government_verification" / filename,
            Path.cwd() / "data" / "mock" / filename
        ]
        for path in search_locations:
            if path.exists():
                return path
        return search_locations[0]

settings = Settings()