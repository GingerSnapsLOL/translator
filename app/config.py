"""Application configuration management.

Settings are read from environment variables (and an optional ``.env`` file)
using Pydantic Settings, then cached so the configuration is loaded once and
reused across the application.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are resolved from, in order of precedence: environment variables,
    a ``.env`` file, then the defaults defined here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # ``model_name`` would otherwise collide with Pydantic's reserved
        # ``model_`` namespace and emit a warning.
        protected_namespaces=(),
    )

    model_name: str = "facebook/nllb-200-distilled-600M"
    device: str = "cpu"
    api_title: str = "Translator API"
    api_version: str = "0.1.0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton ``Settings`` instance.

    The result is cached so configuration is parsed only once per process and
    the same object is reused everywhere it is injected.
    """
    return Settings()
