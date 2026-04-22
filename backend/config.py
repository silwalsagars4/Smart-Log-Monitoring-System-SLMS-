"""
Application configuration via pydantic-settings.
All values read from environment variables / .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "SLMS — Smart Log Monitoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Security
    JWT_SECRET: str = "change-me-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Databases
    MONGO_URL: str = "mongodb://slms:slmspassword@localhost:27017/slms?authSource=admin"
    POSTGRES_URL: str = "postgresql+asyncpg://slms:slmspassword@localhost:5432/slms"
    REDIS_URL: str = "redis://localhost:6379"

    # Alerting
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_FROM: str = "slms@example.com"
    ALERT_TO: str = "admin@example.com"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Feature flags
    ENABLE_GEOIP: bool = False
    ENABLE_TELEGRAM: bool = False
    ENABLE_EMAIL: bool = False

    # GeoIP
    MAXMIND_LICENSE_KEY: str = ""

    # ML
    ML_CONTAMINATION: float = 0.05
    ML_RETRAIN_INTERVAL_HOURS: int = 6
    ML_MODEL_PATH: str = "/app/models/isolation_forest.pkl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
