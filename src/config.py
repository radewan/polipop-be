from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    SEED_ADMIN_PASSWORD: str = "admin12345"
    COOKIE_NAME: str = "session_token"
    COOKIE_SECURE: bool = False  # set True di production (HTTPS)
    SESSION_TTL_SHORT_HOURS: int = 24
    SESSION_TTL_REMEMBER_DAYS: int = 30
    UPLOAD_DIR: Path = Path("uploads")
    PUBLIC_BASE_URL: str = "http://localhost:8000"  # dipakai membentuk URL gambar
    MAX_IMAGE_BYTES: int = 2 * 1024 * 1024  # 2 MB
    IMAGE_MAX_DIMENSION: int = 1024  # sisi terpanjang, dalam px
    APP_TIMEZONE: str = "Asia/Jakarta"  # dipakai untuk filter tanggal
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
