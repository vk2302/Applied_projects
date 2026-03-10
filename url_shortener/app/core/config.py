from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "URL Shortener Service"
    debug: bool = True

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/shortener"
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "super-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    base_url: str = "http://localhost:8000"
    short_code_length: int = 6

    cleanup_interval_minutes: int = 1
    inactive_delete_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
