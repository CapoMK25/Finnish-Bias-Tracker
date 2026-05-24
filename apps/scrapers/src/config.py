"""Configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from env vars or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str

    # Voyage
    voyage_api_key: str = ""

    # Scraping
    scraper_user_agent: str = "FinnishBiasTracker/0.1"
    scraper_rate_limit_per_source_per_minute: int = 10

    # LLM
    llm_scoring_model: str = "claude-haiku-4-5-20251001"
    llm_spot_check_model: str = "claude-sonnet-4-5"
    llm_prompt_version: str = "v1.0"


settings = Settings()  # type: ignore[call-arg]
