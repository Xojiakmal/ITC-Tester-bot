from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = "dummy_token_for_tests"
    BOT_USERNAME: Optional[str] = None

    DATABASE_URL: str = "sqlite+aiosqlite:///./ittestbot.db"

    SECRET_KEY: str = "default_secret_key_needs_override_in_env_32chars"
    JOIN_CODE_PEPPER: str = "default_pepper_key_needs_override_in_env_32chars"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    ADMIN_SESSION_COOKIE_NAME: str = "ittestbot_admin_session"
    COOKIE_SECURE: bool = False

    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET_TOKEN: Optional[str] = None

    MAX_GROUPS_PER_USER: int = 20
    MAX_QUESTIONS_PER_USER: int = 500
    MAX_SCHEDULES_PER_USER: int = 50

    SCHEDULER_INTERVAL_SECONDS: int = 10
    SCHEDULER_GRACE_WINDOW_SECONDS: int = 600
    DEFAULT_TIMEZONE: str = "Asia/Tashkent"
    # Randomize the order of answer options in posted quiz polls
    SHUFFLE_POLL_OPTIONS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
