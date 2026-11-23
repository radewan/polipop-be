from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    SEED_ADMIN_PASSWORD: str = "admin12345"
    COOKIE_NAME: str = "session_token"
    COOKIE_SECURE: bool = False  # set True di production (HTTPS)
    SESSION_TTL_SHORT_HOURS: int = 24
    SESSION_TTL_REMEMBER_DAYS: int = 30
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
