"""Database connection and session management using SQLAlchemy."""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings

# SQLite connection args for multi-threaded FastAPI execution
connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for yielding a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create tables and initialize default records if needed."""
    from backend import models
    from backend.auth.security import get_password_hash

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Populate default system settings and default admin user
    with SessionLocal() as session:
        # Check default user
        admin = session.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        if not admin:
            admin_user = models.User(
                email="admin@cctv.local",
                full_name="Surveillance Admin",
                hashed_password=get_password_hash("AdminPass123!"),
                role="admin",
                is_active=True,
            )
            session.add(admin_user)

        # Check default camera
        cam = session.query(models.Camera).filter(models.Camera.device_index == 0).first()
        if not cam:
            default_cam = models.Camera(
                name="Main Entrance Camera (Default)",
                device_index=0,
                resolution_width=settings.DEFAULT_FRAME_WIDTH,
                resolution_height=settings.DEFAULT_FRAME_HEIGHT,
                fps=settings.DEFAULT_CAMERA_FPS,
                is_connected=False,
                status="standby",
            )
            session.add(default_cam)

        # Seed default settings in key-value table
        default_settings = {
            "motion_sensitivity": str(settings.MOTION_SENSITIVITY),
            "motion_threshold_percent": str(settings.MOTION_THRESHOLD_PERCENT),
            "idle_timeout_seconds": str(settings.IDLE_TIMEOUT_SECONDS),
            "deep_idle_timeout_seconds": str(settings.DEEP_IDLE_TIMEOUT_SECONDS),
            "active_sampling_fps": str(settings.ACTIVE_SAMPLING_FPS),
            "idle_sampling_fps": str(settings.IDLE_SAMPLING_FPS),
            "deep_idle_sampling_fps": str(settings.DEEP_IDLE_SAMPLING_FPS),
            "storage_retention_days": str(settings.STORAGE_RETENTION_DAYS),
            "theme": "dark",
        }

        for key, value in default_settings.items():
            setting = session.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
            if not setting:
                session.add(models.SystemSetting(key=key, value=value, description=f"Default {key}"))

        session.commit()
