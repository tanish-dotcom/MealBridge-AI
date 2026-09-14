"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    app_name: str = "MealBridge AI"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database (SQLite by default; .db file lives in the backend directory)
    database_url: str = "sqlite+aiosqlite:///./mealbridge.db"
    sync_database_url: str = "sqlite+aiosqlite:///./mealbridge.db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate limiting
    rate_limit_default: str = "60/minute"

    # Geo / matching
    use_postgis: bool = False
    avg_city_speed_kmh: float = 30.0
    match_initial_radius_km: float = 5.0
    match_max_radius_km: float = 25.0
    match_radius_step_km: float = 5.0
    match_min_candidates: int = 3
    match_max_alternatives: int = 4
    match_w_distance: float = 0.5
    match_w_capacity: float = 0.3
    match_w_reliability: float = 0.2
    ngo_response_window_minutes: int = 60
    donation_expiry_hours: int = 12

    # Geocoding / directions
    geocoder_provider: str = "nominatim"
    google_maps_api_key: str = ""
    directions_provider: str = "osrm"
    osrm_url: str = "https://router.project-osrm.org/route/v1"

    # Storage
    storage_provider: str = "local"
    local_storage_dir: str = "./storage"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_public_base_url: str = ""

    # Notifications
    email_provider: str = "console"
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "MealBridge AI <no-reply@mealbridge.ai>"
    sms_provider: str = "none"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Impact analytics
    co2_factor_kg_per_kg: float = 2.5
    avg_meal_weight_kg: float = 0.45
    people_per_meal: float = 1.0

    # Seed
    seed_admin_email: str = "admin@mealbridge.ai"
    seed_admin_password: str = "Admin@12345"
    seed_city: str = "Bengaluru"
    seed_city_lat: float = 12.9716
    seed_city_lng: float = 77.5946

    @field_validator("match_w_distance", "match_w_capacity", "match_w_reliability")
    @classmethod
    def _validate_weights(cls, v: float) -> float:
        return v

    @field_validator("database_url", "sync_database_url")
    @classmethod
    def _resolve_sqlite_path(cls, v: str) -> str:
        """Make relative SQLite file paths absolute, anchored to the backend dir."""
        if v.startswith("sqlite") and "///" in v:
            prefix, _, path = v.partition("///")
            if path and not Path(path).is_absolute():
                return f"{prefix}///{(BACKEND_DIR / path).as_posix()}"
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def weight_sum(self) -> float:
        return self.match_w_distance + self.match_w_capacity + self.match_w_reliability


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
