"""
Central configuration for VANTA.

Philosophy reminder (see docs/PHILOSOPHY.md):
    The LLM interprets reality. The server owns reality.
    Deterministic where truth matters. Probabilistic where language matters.
"""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./vanta.db"

    # --- LLM providers ---
    mock_llm: bool = True  # Safe default: works with zero API keys.

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"

    # Provider fallback order used when an agent's preferred provider fails.
    provider_fallback_order: list[str] = ["gemini", "groq", "mock"]

    # --- Admin ---
    admin_username: str = "admin"
    admin_password: str = "change-me"

    # --- Scenario loading ---
    scenarios_dir: str = "scenarios"

    # --- Security ---
    max_message_length: int = 2000
    conversation_history_limit: int = 30  # messages kept in LLM context window


@lru_cache
def get_settings() -> Settings:
    return Settings()
