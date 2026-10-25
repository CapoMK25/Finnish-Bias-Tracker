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
    llm_provider: Literal["anthropic", "mistral"] = "mistral"

    # Mistral (scoring, cluster titles, embeddings)
    mistral_api_key: str = ""
    # "-latest" aliases are fine while evaluating; pin a dated model ID before
    # production so scores stay reproducible when Mistral updates the alias.
    mistral_scoring_model: str = "codestral-2508"
    # Output size must match the vector(N) column in apps/api/src/db/schema.ts.
    mistral_embedding_model: str = "codestral-embed"

    # Anthropic (legacy scorer; remove together with anthropic_scorer.py)
    anthropic_api_key: str = ""
    llm_scoring_model: str = "claude-haiku-4-5-20251001"
    llm_spot_check_model: str = "claude-sonnet-4-5"

    # Scraping
    scraper_user_agent: str = "FinnishBiasTracker/0.1"
    scraper_rate_limit_per_source_per_minute: int = 10

    # LLM config (provider-agnostic)
    llm_prompt_version: str = "v1.2"


settings = Settings()  # type: ignore[call-arg]
