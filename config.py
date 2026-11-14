import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load the project-local .env even when the app is launched from another folder.
load_dotenv(BASE_DIR / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'trr_news.db'}")
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(8 * 1024 * 1024)))
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "/tmp/trr-news-uploads" if os.getenv("VERCEL") else str(BASE_DIR / "app" / "static" / "uploads")))
    MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "25000000"))
    VERCEL_RUNTIME = _as_bool(os.getenv("VERCEL"), False)
    # Google authentication is disabled in this release. Keep this flag for a future re-enable.
    GOOGLE_AUTH_ENABLED = _as_bool(os.getenv("GOOGLE_AUTH_ENABLED"), False)
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = _as_bool(os.getenv("REMEMBER_COOKIE_SECURE"), False)
    WTF_CSRF_TIME_LIMIT = 3600
    AUTO_CREATE_DB = _as_bool(os.getenv("AUTO_CREATE_DB"), False)
    SEED_SAMPLE_CONTENT = _as_bool(os.getenv("SEED_SAMPLE_CONTENT"), False)
    RATELIMIT_ENABLED = _as_bool(os.getenv("RATELIMIT_ENABLED"), True)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    PREFERRED_URL_SCHEME = "https"
    TRR_SITE_NAME = "TRR NEWS"
    TRR_SITE_URL = os.getenv("TRR_SITE_URL", "http://127.0.0.1:5000").rstrip("/")


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    AUTO_CREATE_DB = True
    SEED_SAMPLE_CONTENT = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
