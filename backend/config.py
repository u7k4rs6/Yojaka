from __future__ import annotations

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Deployment
    yojaka_deployment: Literal["dev", "prod"] = "dev"

    # Database
    database_url: str = "sqlite+aiosqlite:///./yojaka.db"

    # Budget
    session_token_budget: int = 40_000
    max_agent_output_tokens: int = 400
    context_window_turns: int = 6

    # Provider keys
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    fireworks_api_key: Optional[str] = None

    # Defaults
    default_model: str = "gemini-2.0-flash"
    enable_mock_provider: bool = True

    # Session cap (per client_id)
    max_sessions_per_client: int = 10

    # Production
    redis_url: Optional[str] = None
    prometheus_enabled: bool = False


settings = Settings()
