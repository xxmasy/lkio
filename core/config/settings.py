"""LKIO Core Configuration Settings
Loads settings from environment variables and .env.local / .env files.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env.local", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    LKIO_ENV: str = "local"

    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 54329
    POSTGRES_DB: str = "lkio"
    POSTGRES_USER: str = "lkio"
    POSTGRES_PASSWORD: str = "change-me-local-only"

    LKIO_SOURCE_READ_ONLY: bool = True
    LKIO_ALLOW_WRITE_TO_SOURCE: bool = False

    LLM_PROVIDER: str = "none"
    DECISION_ENGINE: str = "none"

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
