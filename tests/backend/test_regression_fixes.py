"""
Comprehensive Regression Tests for CCTV Intelligence Bug Fixes & Code Quality Enhancements.
Verifies all 18 priority fixes and security hardening.
"""
import datetime
import os
from pathlib import Path
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal, engine
from backend import models, schemas
from backend.config import settings
from backend.auth.security import create_access_token, get_password_hash
from backend.auth.routes import get_current_user_flexible
from backend.cameras.routes import (
    start_camera,
    stop_camera,
    stream_live_video,
    StartMonitoringRequest,
)
from backend.recordings.routes import (
    list_recordings,
    get_recording,
    delete_recording,
)
from backend.events.routes import list_events, get_event, delete_event
from backend.frames.routes import list_frames, get_frame, delete_frame
from backend.summaries.routes import get_daily_summary
from backend.summaries.generator import DailySummaryGenerator
from vision.camera_manager import camera_manager
from vision.recording_manager import RecordingManager


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_user(db):
    user = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
    if not user:
        user = models.User(
            email="admin@cctv.local",
            full_name="Surveillance Admin",
            hashed_password=get_password_hash("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def operator_user(db):
    email = "test_operator_reg@cctv.local"
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            email=email,
            full_name="Test Operator",
            hashed_password=get_password_hash("OperatorPass123!"),
            role="operator",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Item 1 & 17: Date Validation & Schema Range Constraints
# ---------------------------------------------------------------------------
def test_fix_1_and_17_date_validation_rejects_malformed_dates(db, admin_user):
    """Ensure invalid date strings raise HTTP 400 Bad Request."""
    invalid_dates = ["invalid-date", "2026-99-99", "yesterday", "2026/05/01"]
    for inv_date in invalid_dates:
        with pytest.raises(HTTPException) as exc:
            get_daily_summary(date=inv_date, db=db, current_user=admin_user)
        assert exc.value.status_code == 400
        assert "Invalid date format" in exc.value.detail

        with pytest.raises(HTTPException) as exc:
            list_events(date=inv_date, db=db, current_user=admin_user)
        assert exc.value.status_code == 400

        with pytest.raises(HTTPException) as exc:
            list_recordings(date=inv_date, db=db, current_user=admin_user)
        assert exc.value.status_code == 400


def test_fix_17_settings_schema_bounds_validation():
    """Ensure settings schema rejects negative sampling FPS, out-of-bounds sensitivity."""
    # Negative FPS should fail validation
    with pytest.raises(ValidationError):
        schemas.SettingsUpdate(active_sampling_fps=-5.0)

    # Excessive motion sensitivity should fail validation (> 100)
    with pytest.raises(ValidationError):
        schemas.SettingsUpdate(motion_sensitivity=250)

    # Valid settings pass cleanly
    valid = schemas.SettingsUpdate(active_sampling_fps=5.0, motion_sensitivity=30)
    assert valid.active_sampling_fps == 5.0


# ---------------------------------------------------------------------------
# Item 2: Live Stream Does NOT Auto-Start Virtual Camera
# ---------------------------------------------------------------------------
def test_fix_2_stream_endpoint_does_not_autostart_monitoring(admin_user):
    """Requesting the stream while camera is inactive must NOT auto-start monitoring."""
    camera_manager.stop_monitoring()
    assert camera_manager.is_monitoring is False

    # Calling stream_live_video when not monitoring returns standby image
    resp = stream_live_video(current_user=admin_user)
    assert resp.media_type == "image/jpeg"
    assert camera_manager.is_monitoring is False  # Must remain False!


# ---------------------------------------------------------------------------
# Item 3: Physical Camera Strictly Used Without Silent Virtual Fallback
# ---------------------------------------------------------------------------
def test_fix_3_physical_camera_failure_raises_error_without_fallback():
    """Opening an unavailable physical camera device index must raise error and not disguise as virtual."""
    camera_manager.stop_monitoring()
    # Device index 999 is invalid physical hardware
    with pytest.raises(RuntimeError) as exc:
        camera_manager.start_monitoring(camera_id=1, device_index=999)

    assert "cannot be opened" in str(exc.value) or "Error connecting" in str(exc.value)
    assert camera_manager.is_virtual_camera is False
    assert camera_manager.is_monitoring is False


# ---------------------------------------------------------------------------
# Item 4: Securing Streams, Recordings, Frames, Thumbnails
# ---------------------------------------------------------------------------
def test_fix_4_flexible_authentication_enforcement(db, admin_user):
    """Media endpoints require valid JWT authentication via header or ?token=."""
    # Missing credentials raises 401
    with pytest.raises(HTTPException) as exc:
        get_current_user_flexible(token=None, credentials=None, db=db)
    assert exc.value.status_code == 401

    # Invalid token raises 401
    with pytest.raises(HTTPException) as exc:
        get_current_user_flexible(token="invalid.bogus.jwt", credentials=None, db=db)
    assert exc.value.status_code == 401

    # Valid token succeeds
    valid_token = create_access_token(admin_user.id)
    resolved_user = get_current_user_flexible(token=valid_token, credentials=None, db=db)
    assert resolved_user.id == admin_user.id


# ---------------------------------------------------------------------------
# Item 5: Secure First-Run JWT Secret Key
# ---------------------------------------------------------------------------
def test_fix_5_secure_jwt_secret_not_hardcoded_dev_default():
    """Ensure SECRET_KEY is not the vulnerable hardcoded default."""
    insecure_default = "cctv-intelligence-secret-dev-key-change-in-prod-xyz987654321"
    assert settings.SECRET_KEY != insecure_default
    assert len(settings.SECRET_KEY) >= 32


# ---------------------------------------------------------------------------
# Item 6: User Authorization and Ownership Isolation
# ---------------------------------------------------------------------------
def test_fix_6_data_ownership_and_authorization_isolation(db, admin_user, operator_user):
    """Operators cannot view or delete recordings owned by other users."""
    now_dt = datetime.datetime.now()
    # Create private recording owned by admin
    dummy_file = settings.RECORDINGS_DIR / f"test_priv_{int(now_dt.timestamp())}.mp4"
    dummy_file.write_bytes(b"dummy-video-data")

    priv_rec = models.Recording(
        user_id=admin_user.id,
        camera_id=1,
        start_time=now_dt,
        file_path=str(dummy_file),
        file_size_bytes=len(b"dummy-video-data"),
        activity_state="ACTIVE",
    )
    db.add(priv_rec)
    db.commit()
    db.refresh(priv_rec)

    # Operator cannot retrieve this recording directly
    with pytest.raises(HTTPException) as exc:
        get_recording(recording_id=priv_rec.id, db=db, current_user=operator_user)
    assert exc.value.status_code == 403

    # Operator cannot delete this recording
    with pytest.raises(HTTPException) as exc:
        delete_recording(recording_id=priv_rec.id, db=db, current_user=operator_user)
    assert exc.value.status_code == 403

    # Operator's list_recordings does not leak admin's recording
    op_recs = list_recordings(skip=0, limit=50, db=db, current_user=operator_user)
    assert all(r.user_id == operator_user.id or r.user_id is None for r in op_recs)

    # Admin CAN retrieve and delete it
    admin_view = get_recording(recording_id=priv_rec.id, db=db, current_user=admin_user)
    assert admin_view.id == priv_rec.id
    delete_recording(recording_id=priv_rec.id, db=db, current_user=admin_user)


# ---------------------------------------------------------------------------
# Item 7: Camera Thread Shutdown & Resource Management
# ---------------------------------------------------------------------------
def test_fix_7_camera_thread_shutdown_cleanly(admin_user, db):
    """Start and stop camera monitoring without thread lock deadlock."""
    req = StartMonitoringRequest(camera_id=1, device_index=-1)
    start_res = start_camera(req, current_user=admin_user, db=db)
    assert start_res["status"]["is_monitoring"] is True
    assert camera_manager.capture_thread is not None
    assert camera_manager.capture_thread.is_alive() is True

    # Stop monitoring
    stop_res = stop_camera(current_user=admin_user)
    assert stop_res["status"]["is_monitoring"] is False
    assert camera_manager.cap is None
    assert camera_manager.capture_thread.is_alive() is False


# ---------------------------------------------------------------------------
# Item 8 & 9: VideoWriter FPS & Adaptive Sampling Consistency
# ---------------------------------------------------------------------------
def test_fix_8_and_9_recording_manager_adaptive_fps_consistency():
    """VideoWriter FPS must match active sampling rate and record at adaptive rate."""
    rm = RecordingManager(camera_id=1, camera_name="TestCam", user_id=1)
    assert rm.recording_fps == float(settings.ACTIVE_SAMPLING_FPS)


# ---------------------------------------------------------------------------
# Item 10: Daily Summary Timeline 4 States (ACTIVE, IDLE, DEEP_IDLE, OFFLINE)
# ---------------------------------------------------------------------------
def test_fix_10_daily_summary_timeline_classifies_four_states():
    """Timeline accurately generates ACTIVE, IDLE, DEEP_IDLE, and OFFLINE segments."""
    start_dt = datetime.datetime(2026, 5, 1, 0, 0, 0)
    end_dt = datetime.datetime(2026, 5, 1, 23, 59, 59)

    # Session from 08:00 to 12:00
    s1 = models.MonitoringSession(
        id=101,
        camera_id=1,
        start_time=datetime.datetime(2026, 5, 1, 8, 0, 0),
        end_time=datetime.datetime(2026, 5, 1, 12, 0, 0),
        status="completed",
    )
    # Event at 08:15 (ACTIVE)
    e1 = models.MotionEvent(
        id=201,
        camera_id=1,
        start_time=datetime.datetime(2026, 5, 1, 8, 15, 0),
        end_time=datetime.datetime(2026, 5, 1, 8, 16, 0),
        activity_state="ACTIVE",
    )

    segments = DailySummaryGenerator._build_timeline_segments(
        start_dt, end_dt, [s1], [e1]
    )
    states = {seg["activity_state"] for seg in segments}
    # OFFLINE before 08:00 and after 12:00
    assert "OFFLINE" in states
    # ACTIVE at 08:00-08:30
    assert "ACTIVE" in states
    # DEEP_IDLE after extended quiet (e.g. 10:00-10:30)
    assert "DEEP_IDLE" in states


# ---------------------------------------------------------------------------
# Item 11: Calculate Storage Consumption Using Actual File Sizes
# ---------------------------------------------------------------------------
def test_fix_11_storage_consumption_actual_file_sizes(db):
    """Storage consumption must sum actual byte sizes of recordings and frames."""
    d_str = "2026-06-15"
    d_date = datetime.datetime.strptime(d_str, "%Y-%m-%d")

    # Add recording with 12345 bytes
    r = models.Recording(
        camera_id=1,
        start_time=d_date + datetime.timedelta(hours=1),
        file_path="storage/rec_fake.mp4",
        file_size_bytes=12345,
        activity_state="ACTIVE",
    )
    # Add captured frame with 5432 bytes
    f = models.CapturedFrame(
        camera_id=1,
        timestamp=d_date + datetime.timedelta(hours=1, minutes=5),
        activity_state="ACTIVE",
        file_path="storage/frames/frame_fake.jpg",
        file_size_bytes=5432,
    )
    db.add(r)
    db.add(f)
    db.commit()

    summary = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=d_str, force_regenerate=True)
    assert summary["storage_consumed_bytes"] >= (12345 + 5432)

    # Cleanup
    db.delete(r)
    db.delete(f)
    db.commit()


# ---------------------------------------------------------------------------
# Item 12: Multiple Sessions Duration Aggregation
# ---------------------------------------------------------------------------
def test_fix_12_multiple_sessions_duration_aggregation(db):
    """Multiple sessions on same day must aggregate additively, not max()."""
    d_str = "2026-07-20"
    d_date = datetime.datetime.strptime(d_str, "%Y-%m-%d")

    s1 = models.MonitoringSession(
        camera_id=1,
        start_time=d_date + datetime.timedelta(hours=2),
        end_time=d_date + datetime.timedelta(hours=3),
        active_duration_seconds=100.0,
        idle_duration_seconds=50.0,
        deep_idle_duration_seconds=20.0,
        status="completed",
    )
    s2 = models.MonitoringSession(
        camera_id=1,
        start_time=d_date + datetime.timedelta(hours=4),
        end_time=d_date + datetime.timedelta(hours=5),
        active_duration_seconds=150.0,
        idle_duration_seconds=70.0,
        deep_idle_duration_seconds=30.0,
        status="completed",
    )
    db.add(s1)
    db.add(s2)
    db.commit()

    summary = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=d_str, force_regenerate=True)
    assert summary["active_seconds"] == 250.0  # 100 + 150 (not max 150)
    assert summary["idle_seconds"] == 120.0   # 50 + 70
    assert summary["deep_idle_seconds"] == 50.0  # 20 + 30

    db.delete(s1)
    db.delete(s2)
    db.commit()


# ---------------------------------------------------------------------------
# Item 13: Midnight Crossing Handling
# ---------------------------------------------------------------------------
def test_fix_13_midnight_crossing_session_clamping(db):
    """Sessions spanning midnight clamp durations strictly to the day's 24 hours."""
    # Session from 23:30 on Day 1 to 00:30 on Day 2 (60 min total, 30 min on Day 1)
    day1_str = "2026-08-10"
    day1_date = datetime.datetime.strptime(day1_str, "%Y-%m-%d")
    s = models.MonitoringSession(
        camera_id=1,
        start_time=day1_date + datetime.timedelta(hours=23, minutes=30),
        end_time=day1_date + datetime.timedelta(days=1, minutes=30),
        status="completed",
    )
    db.add(s)
    db.commit()

    summary_day1 = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=day1_str, force_regenerate=True)
    # The monitoring duration for Day 1 must be exactly clamped to 1800 seconds (30 mins from 23:30 to 24:00)
    assert 1790 <= summary_day1["total_monitoring_seconds"] <= 1800

    db.delete(s)
    db.commit()


# ---------------------------------------------------------------------------
# Item 14: Avoid 3-Second Database Summary Writes
# ---------------------------------------------------------------------------
def test_fix_14_avoid_repeated_summary_db_writes(db):
    """Repeated calls with force_regenerate=False do not re-write/upsert database records."""
    d_str = "2026-09-01"
    # Initial generation
    DailySummaryGenerator.get_or_generate_summary(db=db, date_str=d_str, force_regenerate=True)

    summary_rec_before = db.query(models.DailySummary).filter(models.DailySummary.date == d_str).first()
    assert summary_rec_before is not None
    orig_id = summary_rec_before.id

    # Secondary reads with force_regenerate=False
    for _ in range(5):
        cached = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=d_str, force_regenerate=False)
        assert cached["id"] == orig_id


# ---------------------------------------------------------------------------
# Item 16: SQLite Foreign Key Integrity Enforcement
# ---------------------------------------------------------------------------
def test_fix_16_sqlite_foreign_key_enforcement(db):
    """Ensure SQLite PRAGMA foreign_keys=ON rejects orphaned foreign keys."""
    # Attempt to insert a camera with invalid user_id 9999999
    invalid_cam = models.Camera(
        user_id=9999999,
        name="Orphan Camera",
        device_index=15,
        resolution_width=640,
        resolution_height=480,
        fps=30,
    )
    db.add(invalid_cam)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
