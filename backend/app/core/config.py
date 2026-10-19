from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CloudPulse"
    app_version: str = "1.1.0"
    environment: Literal["development", "test", "production"] = "development"
    commit_sha: str = "local"
    database_url: str = "postgresql+psycopg://cloudpulse:cloudpulse@postgres:5432/cloudpulse"
    public_base_url: str = "http://backend:8000"
    frontend_dist: Path = Path("/app/static")
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_password_hash: str = ""
    session_ttl_hours: int = 8
    cookie_name: str = "cloudpulse_session"
    csrf_cookie_name: str = "cloudpulse_csrf"
    request_timeout_seconds: float = 8.0
    max_response_bytes: int = 262_144
    max_monitor_concurrency: int = 4
    monitor_lease_seconds: int = 120
    frankfurter_stale_after_days: int = 5

    @property
    def origin_list(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.allowed_origins.split(",") if origin.strip()]
        public_origin = self.public_base_url.rstrip("/")
        if public_origin not in origins:
            origins.append(public_origin)
        return origins

    @property
    def secure_cookies(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def require_https_in_production(self) -> Settings:
        if self.environment == "production" and not self.public_base_url.startswith("https://"):
            raise ValueError("PUBLIC_BASE_URL must use HTTPS in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

