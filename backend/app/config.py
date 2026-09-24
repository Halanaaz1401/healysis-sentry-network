import os
from pathlib import Path
from typing import List, Union, Optional, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Healysis Core Telemetry Network"
    VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    ENABLE_DOCS: Optional[bool] = None
    TESTING: bool = False
    ALLOW_DEMO_TOKENS: Optional[bool] = None

    # Deterministic Escalation SLA Thresholds (Issue 7: centralized configuration)
    ESCALATION_CRITICAL_TIMEOUT_MINUTES: int = int(os.getenv("ESCALATION_CRITICAL_TIMEOUT_MINUTES", "15"))
    ESCALATION_WARNING_TIMEOUT_MINUTES: int = int(os.getenv("ESCALATION_WARNING_TIMEOUT_MINUTES", "60"))

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.ALLOW_DEMO_TOKENS is None:
            self.ALLOW_DEMO_TOKENS = False if self.APP_ENV.lower() == "production" else True
        if self.ENABLE_DOCS is None:
            self.ENABLE_DOCS = False if self.APP_ENV.lower() == "production" else True
    
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
