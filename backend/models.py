"""SQLAlchemy Database Models for CCTV Intelligence."""
import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="operator")  # "admin", "operator", "viewer"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    device_index = Column(Integer, default=0)
    rtsp_url = Column(String(512), nullable=True)
    is_connected = Column(Boolean, default=False)
    resolution_width = Column(Integer, default=640)
    resolution_height = Column(Integer, default=480)
    fps = Column(Integer, default=30)
    status = Column(String(50), default="standby")  # "standby", "monitoring", "error", "disconnected"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", backref="cameras")
    sessions = relationship("MonitoringSession", back_populates="camera", cascade="all, delete-orphan")
    motion_events = relationship("MotionEvent", back_populates="camera", cascade="all, delete-orphan")
    frames = relationship("CapturedFrame", back_populates="camera", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="camera", cascade="all, delete-orphan")

class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    total_frames = Column(Integer, default=0)
    active_duration_seconds = Column(Float, default=0.0)
    idle_duration_seconds = Column(Float, default=0.0)
    deep_idle_duration_seconds = Column(Float, default=0.0)
    status = Column(String(50), default="active")  # "active", "completed", "aborted"

    # Relationships
    user = relationship("User", backref="monitoring_sessions")
    camera = relationship("Camera", back_populates="sessions")
    events = relationship("MotionEvent", back_populates="session", cascade="all, delete-orphan")
    frames = relationship("CapturedFrame", back_populates="session", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="session", cascade="all, delete-orphan")

class MotionEvent(Base):
    __tablename__ = "motion_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("monitoring_sessions.id"), nullable=True, index=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    peak_motion_score = Column(Float, default=0.0)
    activity_state = Column(String(50), default="ACTIVE")  # "ACTIVE", "IDLE", "DEEP_IDLE"
    frame_count = Column(Integer, default=0)
    thumbnail_path = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="motion_events")
    camera = relationship("Camera", back_populates="motion_events")
    session = relationship("MonitoringSession", back_populates="events")
    frames = relationship("CapturedFrame", back_populates="event")
    recordings = relationship("Recording", back_populates="event")

class CapturedFrame(Base):
    __tablename__ = "captured_frames"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("monitoring_sessions.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("motion_events.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    activity_state = Column(String(50), nullable=False)  # "ACTIVE", "IDLE", "DEEP_IDLE"
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    motion_score = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", backref="captured_frames")
    camera = relationship("Camera", back_populates="frames")
    session = relationship("MonitoringSession", back_populates="frames")
    event = relationship("MotionEvent", back_populates="frames")

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("monitoring_sessions.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("motion_events.id"), nullable=True, index=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    thumbnail_path = Column(String(512), nullable=True)
    activity_state = Column(String(50), default="ACTIVE")

    # Relationships
    user = relationship("User", backref="recordings")
    camera = relationship("Camera", back_populates="recordings")
    session = relationship("MonitoringSession", back_populates="recordings")
    event = relationship("MotionEvent", back_populates="recordings")

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String(10), index=True, nullable=False)  # "YYYY-MM-DD"
    total_monitoring_seconds = Column(Float, default=0.0)
    active_seconds = Column(Float, default=0.0)
    idle_seconds = Column(Float, default=0.0)
    deep_idle_seconds = Column(Float, default=0.0)
    total_motion_events = Column(Integer, default=0)
    total_frames_captured = Column(Integer, default=0)
    total_frames_saved = Column(Integer, default=0)
    storage_consumed_bytes = Column(Integer, default=0)
    first_activity_time = Column(DateTime, nullable=True)
    last_activity_time = Column(DateTime, nullable=True)
    peak_activity_hour = Column(Integer, nullable=True)  # 0 to 23
    narrative_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", backref="daily_summaries")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_daily_summary"),
    )

class SystemSetting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
