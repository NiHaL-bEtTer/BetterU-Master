"""Application settings, read from environment variables (and a .env file).

Every external service is optional except the database and the LLM: if a key
is missing, the matching feature is switched off instead of crashing startup.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"  # development | staging | production

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://betteru:betteru@localhost:5432/betteru"

    # ── Auth ─────────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_days: int = 30
    cookie_secure: bool = False  # set true when served over HTTPS

    # ── LLM (any OpenAI-compatible provider; Groq by default) ────────────
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"  # answers + tool calling
    llm_fast_model: str = "openai/gpt-oss-20b"  # small internal jobs
    # For reasoning models (gpt-oss, o-series, Qwen3): low | medium | high. Empty = don't send.
    llm_reasoning_effort: str = "low"
    llm_daily_message_limit: int = 200  # per user, protects your API budget

    # ── Embeddings (local, ONNX — no PyTorch) ────────────────────────────
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384

    # ── Optional services ────────────────────────────────────────────────
    usda_api_key: str = ""  # live USDA lookups when a food isn't in the local table
    tavily_api_key: str = ""  # trusted-domain web search fallback
    youtube_api_key: str = ""  # recipe videos
    sentry_dsn: str = ""

    # ── CORS (only needed when the web app is served from another origin) ─
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
