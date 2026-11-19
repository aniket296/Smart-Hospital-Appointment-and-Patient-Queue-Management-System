"""Application configuration loaded from environment variables (.env)."""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


def parse_cors_origins(raw_origins: str | None) -> str | list[str]:
    """Parse comma-separated CORS_ORIGINS env var or return '*' if wildcard/empty."""
    if not raw_origins or not raw_origins.strip() or raw_origins.strip() == "*":
        return "*"
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins if origins else "*"


def build_mysql_uri(db_name_env: str, default_db_name: str) -> str:
    """Build a SQLAlchemy MySQL+PyMySQL connection URI from environment variables."""
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv(db_name_env, default_db_name)

    encoded_user = quote_plus(user)
    if password:
        encoded_pw = quote_plus(password)
        auth = f"{encoded_user}:{encoded_pw}"
    else:
        auth = encoded_user

    return f"mysql+pymysql://{auth}@{host}:{port}/{db_name}?charset=utf8mb4"


class Config:
    """Base configuration for local development."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-change-in-production")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
    HOSPITAL_TIMEZONE = os.getenv("HOSPITAL_TIMEZONE", "Asia/Kolkata")
    CORS_ORIGINS = parse_cors_origins(os.getenv("CORS_ORIGINS", "*"))

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        build_mysql_uri("DB_NAME", "hospital_queue_db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # SMTP Configuration (optional; defaults gracefully to SIMULATED mode if unset)
    SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@hospital.test").strip()
    SMTP_TIMEOUT_SECONDS = 10


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class TestingConfig(Config):
    """Testing configuration using separate test database."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        build_mysql_uri("TEST_DB_NAME", "hospital_queue_test_db"),
    )


class ProductionConfig(Config):
    """Production configuration for self-hosted deployments."""

    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
