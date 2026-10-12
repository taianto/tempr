from functools import lru_cache
import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def prepare_database_path(database_url: str) -> None:
    """Create the parent directory for a relative SQLite database URL."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and not database_url.startswith("sqlite:////"):
        path = Path(database_url[len(prefix):])
        if path.name:
            path.parent.mkdir(parents=True, exist_ok=True)
