"""Application settings, loaded from environment variables and ``backend/.env``."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    cr_api_key: SecretStr = SecretStr("")
    cr_api_base: str = "https://api.clashroyale.com/v1"
    default_player_tag: str = ""

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'clash.sqlite').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # HTTP client behaviour
    request_timeout_s: float = 15.0
    min_request_interval_s: float = 0.12
    max_retries: int = 3

    # Background polling
    scheduler_enabled: bool = True
    battlelog_poll_minutes: int = 15
    snapshot_min_interval_minutes: int = 60
    auto_refresh_seconds: int = 120
    meta_refresh_hours: int = 24
    meta_top_players: int = Field(default=100, ge=1, le=1000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
