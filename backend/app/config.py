from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    app_name: str = "RYTHU SAHAYA API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./rythu_sahaya.db"
    supabase_database_url: str | None = None
    secret_key: str = "local-development-only-change-me"
    cors_origins: str = "http://localhost:5173"
    google_client_id: str | None = None
    mock_voice_enabled: bool = True
    mock_telephony_enabled: bool = True
    upload_dir: str = "uploads"
    sarvam_api_key: str | None = None
    exotel_api_key: str | None = None
    exotel_api_token: str | None = None
    exotel_sid: str | None = None

    model_config = SettingsConfigDict(env_file=BACKEND_ENV_FILE, case_sensitive=False, extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
