"""
LocalDocRAG configuration — loaded once at startup from environment variables / .env file.

All LLM providers, database, auth, and pipeline settings live here.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Authentication ────────────────────────────────────────────────────────
    APP_USERNAME: str = "admin"
    APP_PASSWORD_HASH: str = Field(
        default="",
        description=(
            "Bcrypt hash of the app password. "
            "Generate: python3 -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
        ),
    )
    JWT_SECRET_KEY: str = Field(
        default="",
        description="Random secret for signing JWT tokens (min 32 chars).",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    # ── LLM Provider ──────────────────────────────────────────────────────────
    # openai | anthropic | ollama
    LLM_PROVIDER: str = "ollama"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_LLM_MODEL: str = "claude-haiku-4-5-20251001"

    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:14b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+psycopg://localdocrag_user:localdocrag_secret_change_me@db:5432/localdocrag"
    )

    # ── RAG Pipeline ─────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    TOP_K_RETRIEVAL: int = 5
    MAX_FILE_SIZE_MB: int = 20
    # Must match the embedding model:
    #   OpenAI text-embedding-3-small → 1536
    #   Ollama nomic-embed-text       → 768
    EMBEDDING_DIMENSION: int = 768

    # ── RAGAS Evaluation ─────────────────────────────────────────────────────
    RAGAS_LLM_MODEL: str = "gpt-4o-mini"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated origins. Add your Pi's local IP (e.g. https://192.168.1.100)
    ALLOWED_ORIGINS: str = (
        "https://localhost,https://localdocrag.local,http://localhost:5173"
    )

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton — imported by all other modules
settings = Settings()
