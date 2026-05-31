"""Configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = four levels up from this file: src/config.py → src/ → scrapers/ → apps/ → root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings, loaded from env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM provider selection
    llm_provider: Literal["anthropic", "gemini"] = "gemini"

    # Anthropic (kept for future use)
    anthropic_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_scoring_model: str = "gemini-2.5-flash"

    # Voyage (M3+)
    voyage_api_key: str = ""

    # Scraping
    scraper_user_agent: str = "FinnishBiasTracker/0.1"
    scraper_rate_limit_per_source_per_minute: int = 10

    # LLM config (provider-agnostic)
    llm_scoring_model: str = "claude-haiku-4-5-20251001"
    llm_spot_check_model: str = "claude-sonnet-4-5"
    llm_prompt_version: str = "v1.1"


settings = Settings()  # type: ignore[call-arg]
