"""Database connection and session management using SQLAlchemy."""
import logging
import sqlite3
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings

logger = logging.getLogger("cctv.database")

# SQLite connection args for multi-threaded FastAPI execution
connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce SQLite foreign key integrity constraints on every connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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


def run_migrations(connection) -> None:
    """Non-destructively apply missing schema migrations to existing SQLite database."""
    cursor = connection.cursor()
    tables = {
        "cameras": [("user_id", "INTEGER REFERENCES users(id)")],
        "monitoring_sessions": [("user_id", "INTEGER REFERENCES users(id)")],
        "motion_events": [("user_id", "INTEGER REFERENCES users(id)")],
        "captured_frames": [
            ("user_id", "INTEGER REFERENCES users(id)"),
            ("file_size_bytes", "INTEGER DEFAULT 0"),
        ],
        "recordings": [("user_id", "INTEGER REFERENCES users(id)")],
        "daily_summaries": [("user_id", "INTEGER REFERENCES users(id)")],
    }

    for table_name, cols_to_add in tables.items():
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_def in cols_to_add:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Applied migration: added column {col_name} to {table_name}")
        except Exception as e:
            logger.warning(f"Error checking/migrating {table_name}: {e}")

    # Backfill existing surveillance data with default admin user ID if user_id is NULL
    try:
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_id = admin_row[0]
            for t in ["cameras", "monitoring_sessions", "motion_events", "captured_frames", "recordings", "daily_summaries"]:
                cursor.execute(f"UPDATE {t} SET user_id = ? WHERE user_id IS NULL", (admin_id,))
    except Exception as e:
        logger.warning(f"Error backfilling user_id: {e}")

    # Migrate daily_summaries unique index: replace UNIQUE index on date with composite UNIQUE on (user_id, date)
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'ix_daily_summaries_date'")
        idx_row = cursor.fetchone()
        if idx_row and "UNIQUE" in (idx_row[0] or "").upper():
            cursor.execute("DROP INDEX IF EXISTS ix_daily_summaries_date")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_daily_summaries_date ON daily_summaries (date)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_daily_summary ON daily_summaries (user_id, date)")
            logger.info("Migrated daily_summaries: replaced UNIQUE index on date with composite UNIQUE index on (user_id, date)")
        else:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_daily_summary ON daily_summaries (user_id, date)")
    except Exception as e:
        logger.warning(f"Error updating daily_summaries index: {e}")

    connection.commit()
    cursor.close()


def init_db() -> None:
    """Create tables, run migrations, and initialize default records with robust error propagation."""
    from backend import models
    from backend.auth.security import get_password_hash

    try:
        # Create tables
        Base.metadata.create_all(bind=engine)

        # Apply safe migrations for existing SQLite databases
        with engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection if hasattr(conn.connection, "dbapi_connection") else conn.connection
            run_migrations(raw_conn)
    except Exception as e:
        logger.error(f"Error during schema initialization or migration: {e}")
        raise RuntimeError(f"Database schema initialization failed: {e}") from e

    try:
        # Populate default system settings and default admin user
        with SessionLocal() as session:
            # Check default user
            admin = session.query(models.User).filter(models.User.email == settings.ADMIN_EMAIL).first()
            if not admin:
                import secrets
                initial_password = settings.ADMIN_PASSWORD
                if not initial_password:
                    initial_password = secrets.token_urlsafe(20)
                    logger.warning("==================================================================")
                    logger.warning("FIRST-RUN ADMIN SETUP: ADMIN_PASSWORD was not configured in .env.")
                    logger.warning(f"Generated secure administrator credentials:")
                    logger.warning(f"  Email:    {settings.ADMIN_EMAIL}")
                    logger.warning(f"  Password: {initial_password}")
                    logger.warning("Please record these credentials or define ADMIN_PASSWORD in .env.")
                    logger.warning("==================================================================")

                admin_user = models.User(
                    email=settings.ADMIN_EMAIL,
                    full_name="Surveillance Admin",
                    hashed_password=get_password_hash(initial_password),
                    role="admin",
                    is_active=True,
                )
                session.add(admin_user)
                session.commit()
                session.refresh(admin_user)
                admin = admin_user

            # Check default camera
            cam = session.query(models.Camera).filter(models.Camera.device_index == 0).first()
            if not cam:
                default_cam = models.Camera(
                    user_id=admin.id if admin else None,
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
    except Exception as e:
        logger.error(f"Error seeding initial database defaults: {e}")
