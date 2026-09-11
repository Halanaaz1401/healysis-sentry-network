import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Healysis Core Telemetry Network"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENABLE_DOCS: bool = os.getenv("ENABLE_DOCS", "true").lower() == "true"
    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"
    ALLOW_DEMO_TOKENS: bool = os.getenv("ALLOW_DEMO_TOKENS", "true").lower() == "true"
    
    # PostgreSQL Primary Database Connection URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://healysis_user:healysis_pass@localhost:5432/healysis_db"
    )
    # Local SQLite fallback URL for development/testing when PostgreSQL is offline
    SQLITE_FALLBACK_URL: str = f"sqlite:///{BASE_DIR}/healysis_local.db"
    
    # Security & Firebase Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "healysis-super-secret-key-2026-production-min-32-bytes")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "healysis-sentry-network")
    FIREBASE_CREDENTIALS_FILE: str = os.getenv("FIREBASE_CREDENTIALS_FILE", "")
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://healysis.ashlynxcyber.in"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def parse_allowed_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            clean_str = v.strip("[]").replace('"', '').replace("'", '')
            return [o.strip() for o in clean_str.split(",") if o.strip()]
        return v

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
