from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/app.db"
    openai_api_key: SecretStr | None = None
    classification_model: str = "gpt-6-luna"
    classification_timeout_seconds: float = Field(default=30.0, gt=0)
    test_generation_model: str | None = None
    test_generation_timeout_seconds: float = Field(default=120.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def prepare_database_path(database_url: str) -> None:
    """Create the parent directory for a relative SQLite database URL."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and not database_url.startswith("sqlite:////"):
        path = Path(database_url[len(prefix) :])
        if path.name:
            path.parent.mkdir(parents=True, exist_ok=True)
