"""Application Configuration Module

Uses Pydantic BaseSettings for strict environment variable parsing,
validation, type safety, and secure credential handling.
"""

import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DEFAULT_DB_FILE = os.path.join(_BACKEND_DIR, "guardian_cfo.db").replace("\\", "/")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Guardian CFO"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        raise ValueError(v)

    # Database Settings
    # Supports PostgreSQL standard (psycopg) and SQLite for zero-friction local dev
    DATABASE_URL: str = f"sqlite:///{_DEFAULT_DB_FILE}"

    # JWT Authentication & Password Security
    JWT_SECRET: str = "super-secret-guardian-cfo-jwt-key-change-in-production-random-salt-9871"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Demo Account Credentials (For safe demo evaluation)
    DEMO_USER_EMAIL: str = "demo@guardiancfo.ai"
    DEMO_USER_PASSWORD: str = "DemoCFO2026!"

    # OpenAI Settings (Structured outputs and tool-calling agent)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # PayPal REST API Configuration (Sandbox by default)
    PAYPAL_MODE: str = "sandbox"  # "sandbox" or "live"
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""

    @property
    def paypal_base_url(self) -> str:
        """Returns PayPal REST API Base URL depending on execution mode."""
        if self.PAYPAL_MODE.lower() == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    # Core Financial Guardrails
    AUTO_APPROVE_THRESHOLD_USD: float = 250.00
    CRITICAL_RISK_THRESHOLD: float = 75.0  # Scale 0-100 (>=75 requires executive review)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
