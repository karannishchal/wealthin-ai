"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # provider selection
    llm_provider: str = "gemini"
    llm_fallback: str = "none"

    # keys
    groq_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # models
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    anthropic_model: str = "claude-haiku-4-5-20251001"
    openai_model: str = "gpt-4o-mini"

    # behaviour
    demo_mode: bool = True
    rate_limit_per_minute: int = 15
    max_agent_steps: int = 4
    scope_guard: bool = False  # scope enforced in the system prompt (saves an LLM call)
    docs_dir: str = "./data/docs"
    log_level: str = "INFO"

    def key_for(self, provider: str) -> str:
        return {
            "groq": self.groq_api_key,
            "gemini": self.gemini_api_key,
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
        }.get(provider, "")

    def model_for(self, provider: str) -> str:
        return {
            "groq": self.groq_model,
            "gemini": self.gemini_model,
            "anthropic": self.anthropic_model,
            "openai": self.openai_model,
        }.get(provider, "")

    def has_any_key(self) -> bool:
        return any(
            self.key_for(p) for p in ("groq", "gemini", "anthropic", "openai")
        )


settings = Settings()
