"""Configuration settings for CCTV Intelligence."""
import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "CCTV Intelligence"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cctv-intelligence-secret-dev-key-change-in-prod-xyz987654321")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@cctv.local")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "AdminPass123!")

    # Database
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'cctv_intelligence.db'}"
    SYNC_DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'cctv_intelligence.db'}"

    # Storage paths (resolved to absolute paths)
    STORAGE_DIR: Path = PROJECT_ROOT / "storage"
    RECORDINGS_DIR: Path = PROJECT_ROOT / "storage" / "recordings"
    FRAMES_DIR: Path = PROJECT_ROOT / "storage" / "frames"
    THUMBNAILS_DIR: Path = PROJECT_ROOT / "storage" / "thumbnails"
    SUMMARIES_DIR: Path = PROJECT_ROOT / "storage" / "summaries"
    STORAGE_RETENTION_DAYS: int = 30

    # Camera Defaults
    DEFAULT_CAMERA_INDEX: int = 0
    DEFAULT_FRAME_WIDTH: int = 640
    DEFAULT_FRAME_HEIGHT: int = 480
    DEFAULT_CAMERA_FPS: int = 30
    ENABLE_VIRTUAL_CAMERA_FALLBACK: bool = True

    # Motion Detection Defaults
    MOTION_SENSITIVITY: int = 25  # MOG2 varThreshold
    MOTION_THRESHOLD_PERCENT: float = 1.5  # Percentage of frame pixels changed to trigger active
    IDLE_TIMEOUT_SECONDS: float = 5.0
    DEEP_IDLE_TIMEOUT_SECONDS: float = 20.0

    # Adaptive Sampling Rates (FPS)
    ACTIVE_SAMPLING_FPS: float = 5.0
    IDLE_SAMPLING_FPS: float = 2.0
    DEEP_IDLE_SAMPLING_FPS: float = 1.0

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Secure first-run secret key generation
_dev_default = "cctv-intelligence-secret-dev-key-change-in-prod-xyz987654321"
if settings.SECRET_KEY == _dev_default:
    _new_secret = secrets.token_hex(32)
    settings.SECRET_KEY = _new_secret
    _env_file = PROJECT_ROOT / ".env"
    if _env_file.exists():
        try:
            _txt = _env_file.read_text(encoding="utf-8")
            if _dev_default in _txt:
                _env_file.write_text(_txt.replace(_dev_default, _new_secret), encoding="utf-8")
        except Exception:
            pass

# Ensure storage directories exist
for directory in [
    settings.STORAGE_DIR,
    settings.RECORDINGS_DIR,
    settings.FRAMES_DIR,
    settings.THUMBNAILS_DIR,
    settings.SUMMARIES_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
