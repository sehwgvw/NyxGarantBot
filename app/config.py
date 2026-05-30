from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    main_admin_id: int = Field(alias="MAIN_ADMIN_ID")
    database_url: str = Field(
        default="postgresql+asyncpg://nyx_garant:nyx_garant_password@localhost:5432/nyx_garant",
        alias="DATABASE_URL",
    )
    default_language: str = Field(default="Russian", alias="DEFAULT_LANGUAGE")
    support_username: str = Field(default="@NyawkaCuteUwU", alias="SUPPORT_USERNAME")
    moderation_group_id: str | None = Field(default=None, alias="MODERATION_GROUP_ID")
    log_group_id: str | None = Field(default=None, alias="LOG_GROUP_ID")
    use_userbot: bool = Field(default=False, alias="USE_USERBOT")
    api_id: int | None = Field(default=None, alias="API_ID")
    api_hash: str | None = Field(default=None, alias="API_HASH")
    session_path: Path = Field(default=Path("sessions/nyx_userbot.session"), alias="SESSION_PATH")
    default_deal_confirm_timeout: int = Field(default=3600, alias="DEFAULT_DEAL_CONFIRM_TIMEOUT")
    default_deal_finish_timeout: int = Field(default=86400, alias="DEFAULT_DEAL_FINISH_TIMEOUT")
    default_dispute_timeout: int = Field(default=86400, alias="DEFAULT_DISPUTE_TIMEOUT")
    max_unpaid_cancels: int = Field(default=3, alias="MAX_UNPAID_CANCELS")
    permanent_block_after_limit: bool = Field(default=True, alias="PERMANENT_BLOCK_AFTER_LIMIT")
    top_guarantor_min_rating: float = Field(default=4.7, alias="TOP_GUARANTOR_MIN_RATING")
    top_guarantor_min_success_deals: int = Field(default=10, alias="TOP_GUARANTOR_MIN_SUCCESS_DEALS")
    backup_enabled: bool = Field(default=True, alias="BACKUP_ENABLED")
    backup_interval_hours: int = Field(default=24, alias="BACKUP_INTERVAL_HOURS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
