"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class Settings:
    """Simple settings container backed by environment variables."""

    groq_api_key: str
    google_api_key: str
    cors_origins: str
    database_url: str

    def __init__(self) -> None:
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        self.cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.database_url = os.getenv("DATABASE_URL", "./data/app.db")

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list, stripping whitespace."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
