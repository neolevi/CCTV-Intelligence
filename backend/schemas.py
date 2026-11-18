"""Pydantic schemas for data validation and API serialization."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Auth & User Schemas ---
class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str

class UserUpdatePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# --- Camera Schemas ---
class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    device_index: int = Field(0, ge=-1, le=32)
    rtsp_url: Optional[str] = None
    resolution_width: int = Field(640, ge=160, le=3840)
    resolution_height: int = Field(480, ge=120, le=2160)
    fps: int = Field(30, ge=1, le=60)

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    device_index: Optional[int] = Field(None, ge=-1, le=32)
    rtsp_url: Optional[str] = None
    resolution_width: Optional[int] = Field(None, ge=160, le=3840)
    resolution_height: Optional[int] = Field(None, ge=120, le=2160)
    fps: Optional[int] = Field(None, ge=1, le=60)

class CameraOut(CameraBase):
    id: int
    is_connected: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CameraDeviceOption(BaseModel):
    index: int
    name: str
    is_available: bool

class CameraStatusOut(BaseModel):
    is_connected: bool
    is_monitoring: bool
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    device_index: Optional[int] = None
    current_fps: float = 0.0
    activity_state: str = "IDLE"  # "ACTIVE", "IDLE", "DEEP_IDLE"
    sampling_fps: float = 2.0
    uptime_seconds: float = 0.0
    total_frames_processed: int = 0
    total_frames_saved: int = 0
    motion_score: float = 0.0

# --- Motion & Adaptive Sampling Schemas ---
class MotionStatusOut(BaseModel):
    activity_state: str  # "ACTIVE", "IDLE", "DEEP_IDLE"
    motion_score: float
    is_motion_detected: bool
    sampling_fps: float
    time_in_current_state: float
    active_timeout_remaining: float

class MotionStatisticsOut(BaseModel):
    active_percentage: float
    idle_percentage: float
    deep_idle_percentage: float
    total_events_today: int
    peak_motion_score_today: float

# --- Frame Schemas ---
class CapturedFrameOut(BaseModel):
    id: int
    camera_id: int
    session_id: Optional[int] = None
    event_id: Optional[int] = None
    timestamp: datetime
    activity_state: str
    file_path: str
    motion_score: float

    class Config:
        from_attributes = True

# --- Event Schemas ---
class MotionEventOut(BaseModel):
    id: int
    camera_id: int
    session_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    peak_motion_score: float
    activity_state: str
    frame_count: int
    thumbnail_path: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

class MotionEventDetail(MotionEventOut):
    frames: List[CapturedFrameOut] = []

# --- Recording Schemas ---
class RecordingOut(BaseModel):
    id: int
    camera_id: int
    session_id: Optional[int] = None
    event_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float
    file_path: str
    file_size_bytes: int
    thumbnail_path: Optional[str] = None
    activity_state: str

    class Config:
        from_attributes = True

# --- Daily Summary Schemas ---
class TimelineSegment(BaseModel):
    start_time: str
    end_time: str
    activity_state: str  # "ACTIVE", "IDLE", "DEEP_IDLE", "OFFLINE"
    duration_seconds: float
    event_count: int = 0

class HourlyActivity(BaseModel):
    hour: int  # 0 to 23
    label: str  # e.g., "00:00", "01:00"
    event_count: int
    active_minutes: float

class DailySummaryDateItem(BaseModel):
    date: str
    total_events: int = 0
    active_seconds: float = 0.0
    total_monitoring_seconds: float = 0.0
    storage_consumed_bytes: int = 0
    has_summary: bool = False

class DailySummaryOut(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    date: str  # "YYYY-MM-DD"
    total_monitoring_seconds: float
    active_seconds: float
    idle_seconds: float
    deep_idle_seconds: float
    total_motion_events: int
    total_frames_captured: int
    total_frames_saved: int
    storage_consumed_bytes: int
    first_activity_time: Optional[datetime] = None
    last_activity_time: Optional[datetime] = None
    peak_activity_hour: Optional[int] = None
    narrative_summary: Optional[str] = None
    timeline_segments: List[TimelineSegment] = []
    hourly_distribution: List[HourlyActivity] = []
    important_events: List[MotionEventOut] = []
    events: List[MotionEventOut] = []

    class Config:
        from_attributes = True

# --- Analytics Schemas ---
class AnalyticsOverviewOut(BaseModel):
    today_active_seconds: float
    today_idle_seconds: float
    today_deep_idle_seconds: float
    total_motion_events_today: int
    total_recordings_count: int
    total_storage_used_bytes: int
    total_monitoring_hours_week: float
    active_ratio_today: float

class AnalyticsTrendsOut(BaseModel):
    dates: List[str]
    active_durations: List[float]
    idle_durations: List[float]
    deep_idle_durations: List[float]
    motion_event_counts: List[int]
    storage_trend_bytes: List[int]

# --- Settings Schemas ---
class SettingsOut(BaseModel):
    motion_sensitivity: int
    motion_threshold_percent: float
    idle_timeout_seconds: float
    deep_idle_timeout_seconds: float
    active_sampling_fps: float
    idle_sampling_fps: float
    deep_idle_sampling_fps: float
    storage_retention_days: int
    theme: str
    default_camera_index: int
    resolution_width: int
    resolution_height: int
    storage_path: str
    storage_used_bytes: int
    storage_free_bytes: int

class SettingsUpdate(BaseModel):
    motion_sensitivity: Optional[int] = Field(None, ge=1, le=100)
    motion_threshold_percent: Optional[float] = Field(None, ge=0.01, le=100.0)
    idle_timeout_seconds: Optional[float] = Field(None, ge=1.0, le=3600.0)
    deep_idle_timeout_seconds: Optional[float] = Field(None, ge=2.0, le=86400.0)
    active_sampling_fps: Optional[float] = Field(None, ge=0.1, le=60.0)
    idle_sampling_fps: Optional[float] = Field(None, ge=0.1, le=30.0)
    deep_idle_sampling_fps: Optional[float] = Field(None, ge=0.1, le=30.0)
    storage_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    theme: Optional[str] = Field(None, pattern=r"^(dark|light)$")
    default_camera_index: Optional[int] = Field(None, ge=-1, le=32)
    resolution_width: Optional[int] = Field(None, ge=160, le=3840)
    resolution_height: Optional[int] = Field(None, ge=120, le=2160)
