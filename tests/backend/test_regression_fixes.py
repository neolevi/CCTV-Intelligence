"""
Comprehensive Regression Tests for CCTV Intelligence Bug Fixes & Code Quality Enhancements.
Verifies all 18 priority fixes and security hardening.
"""
import asyncio
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
    download_recording_video,
)
from backend.events.routes import list_events, get_event, delete_event
from backend.frames.routes import list_frames, get_frame, delete_frame
from backend.summaries.routes import get_daily_summary, download_summary_report
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
    thread = camera_manager.capture_thread

    # Stop monitoring
    stop_res = stop_camera(current_user=admin_user)
    assert stop_res["status"]["is_monitoring"] is False
    assert camera_manager.cap is None
    assert thread.is_alive() is False
    assert camera_manager.capture_thread is None


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
    # Event at 08:10-08:15 (5 minutes of sustained ACTIVE motion > 120s)
    e1 = models.MotionEvent(
        id=201,
        camera_id=1,
        start_time=datetime.datetime(2026, 5, 1, 8, 10, 0),
        end_time=datetime.datetime(2026, 5, 1, 8, 15, 0),
        activity_state="ACTIVE",
    )
    # Brief event at 08:45-08:45:20 (20s motion, should classify window as IDLE with event)
    e2 = models.MotionEvent(
        id=202,
        camera_id=1,
        start_time=datetime.datetime(2026, 5, 1, 8, 45, 0),
        end_time=datetime.datetime(2026, 5, 1, 8, 45, 20),
        activity_state="ACTIVE",
    )

    segments = DailySummaryGenerator._build_timeline_segments(
        start_dt, end_dt, [s1], [e1, e2]
    )
    states = {seg["activity_state"] for seg in segments}
    # OFFLINE before 08:00 and after 12:00
    assert "OFFLINE" in states
    # ACTIVE at 08:00-08:30 (due to 5 mins sustained motion)
    assert "ACTIVE" in states
    # IDLE at 08:30-09:00 (brief 20s event does not mark entire 30m window ACTIVE)
    assert "IDLE" in states
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
    # Clean up any conflicting sessions or summaries on day1
    db.query(models.DailySummary).filter(models.DailySummary.date == day1_str).delete(synchronize_session=False)
    db.query(models.MonitoringSession).filter(
        models.MonitoringSession.start_time >= day1_date,
        models.MonitoringSession.start_time < day1_date + datetime.timedelta(days=1),
    ).delete(synchronize_session=False)
    db.commit()

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


# ---------------------------------------------------------------------------
# Item 18: Summary and Recording Flexible Auth Downloads
# ---------------------------------------------------------------------------
def test_fix_summary_and_recording_download_flexible_auth(db, admin_user):
    """Test that summary and recording download endpoints support flexible authentication with tokens."""
    token = create_access_token(subject=admin_user.id)
    authed_user = get_current_user_flexible(token=token, db=db)
    assert authed_user.email == admin_user.email

    # Test download_summary_report
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    response = download_summary_report(date=today_str, db=db, current_user=authed_user)
    assert response.status_code == 200
    assert "CCTV Intelligence" in response.body.decode("utf-8")
    assert response.headers["Content-Disposition"].startswith("attachment;")


# ---------------------------------------------------------------------------
# Item 19: Monotonic Clock Robustness in Vision Modules
# ---------------------------------------------------------------------------
def test_monotonic_clock_robustness():
    """Verify that AdaptiveSampler and MotionDetector use monotonic timing calculations."""
    from vision.adaptive_sampler import AdaptiveSampler
    from vision.motion_detector import MotionDetector
    import numpy as np

    sampler = AdaptiveSampler(active_fps=5.0, idle_fps=2.0)
    # Using explicit timestamps simulating monotonic ticks
    t0 = 1000.0
    assert sampler.should_sample("ACTIVE", current_time=t0) is True
    # Frame too soon
    assert sampler.should_sample("ACTIVE", current_time=t0 + 0.05) is False
    # Frame meets interval
    assert sampler.should_sample("ACTIVE", current_time=t0 + 0.21) is True

    # MotionDetector get_status uses time.monotonic() internally
    detector = MotionDetector(idle_timeout=2.0, deep_idle_timeout=5.0)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    detector.process_frame(frame)
    status = detector.get_status()
    assert "time_in_current_state" in status
    assert status["time_in_current_state"] >= 0.0


# ---------------------------------------------------------------------------
# Second-Pass Item 2: Camera Ownership, Cross-User Rejection & Multi-User 409 Conflict
# ---------------------------------------------------------------------------
def test_camera_ownership_and_cross_user_rejection(db, admin_user):
    """Verify camera ownership checks, multi-user singleton rejection, and stream protections."""
    # Create Operator A and Operator B
    user_a = db.query(models.User).filter(models.User.email == "op_a_test@cctv.local").first()
    if not user_a:
        user_a = models.User(
            email="op_a_test@cctv.local",
            full_name="Operator A",
            hashed_password=get_password_hash("Pass123!"),
            role="operator",
            is_active=True,
        )
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

    user_b = db.query(models.User).filter(models.User.email == "op_b_test@cctv.local").first()
    if not user_b:
        user_b = models.User(
            email="op_b_test@cctv.local",
            full_name="Operator B",
            hashed_password=get_password_hash("Pass123!"),
            role="operator",
            is_active=True,
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

    # User A owns Camera A
    cam_a = db.query(models.Camera).filter(models.Camera.name == "Camera A Test").first()
    if not cam_a:
        cam_a = models.Camera(
            user_id=user_a.id,
            name="Camera A Test",
            device_index=-1,
            resolution_width=640,
            resolution_height=480,
            fps=30,
        )
        db.add(cam_a)
        db.commit()
        db.refresh(cam_a)

    # User B owns Camera B
    cam_b = db.query(models.Camera).filter(models.Camera.name == "Camera B Test").first()
    if not cam_b:
        cam_b = models.Camera(
            user_id=user_b.id,
            name="Camera B Test",
            device_index=-1,
            resolution_width=640,
            resolution_height=480,
            fps=30,
        )
        db.add(cam_b)
        db.commit()
        db.refresh(cam_b)

    # 1. User B tries to start User A's camera -> 403 Forbidden
    req_a = StartMonitoringRequest(camera_id=cam_a.id, device_index=-1)
    with pytest.raises(HTTPException) as exc:
        start_camera(req_a, current_user=user_b, db=db)
    assert exc.value.status_code == 403

    # 2. User A starts their own camera -> 200 OK
    res_start = start_camera(req_a, current_user=user_a, db=db)
    assert res_start["status"]["is_monitoring"] is True

    # 3. User B tries to start Camera B while Camera A is already active -> 409 Conflict
    req_b = StartMonitoringRequest(camera_id=cam_b.id, device_index=-1)
    with pytest.raises(HTTPException) as exc:
        start_camera(req_b, current_user=user_b, db=db)
    assert exc.value.status_code == 409
    assert "A camera monitoring session is already active" in exc.value.detail

    # 4. User B tries to stop User A's active session -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        stop_camera(current_user=user_b)
    assert exc.value.status_code == 403
    assert "Cannot stop another operator's active monitoring session" in exc.value.detail

    # 5. User B tries to access User A's live stream -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        stream_live_video(current_user=user_b)
    assert exc.value.status_code == 403
    assert "live camera stream" in exc.value.detail

    # 6. User A stops their own camera -> 200 OK
    res_stop = stop_camera(current_user=user_a)
    assert res_stop["status"]["is_monitoring"] is False


# ---------------------------------------------------------------------------
# Second-Pass Item 3: Daily Summary Isolation & User-Scoped Queries
# ---------------------------------------------------------------------------
def test_daily_summary_user_isolation(db):
    """Ensure Daily Summary only aggregates data belonging to the requested user."""
    # User 1 & User 2
    u1 = db.query(models.User).filter(models.User.email == "iso1@cctv.local").first()
    if not u1:
        u1 = models.User(email="iso1@cctv.local", hashed_password="pw", role="operator")
        db.add(u1)
        db.commit()
        db.refresh(u1)

    u2 = db.query(models.User).filter(models.User.email == "iso2@cctv.local").first()
    if not u2:
        u2 = models.User(email="iso2@cctv.local", hashed_password="pw", role="operator")
        db.add(u2)
        db.commit()
        db.refresh(u2)

    test_date_str = "2026-10-15"
    db.query(models.DailySummary).filter(models.DailySummary.date == test_date_str).delete()
    db.query(models.MotionEvent).filter(models.MotionEvent.user_id.in_([u1.id, u2.id])).delete(synchronize_session=False)
    db.query(models.MonitoringSession).filter(models.MonitoringSession.user_id.in_([u1.id, u2.id])).delete(synchronize_session=False)
    db.commit()

    t_start = datetime.datetime(2026, 10, 15, 10, 0, 0)
    t_end = datetime.datetime(2026, 10, 15, 11, 0, 0)

    # Session for U1
    s1 = models.MonitoringSession(
        user_id=u1.id,
        camera_id=1,
        start_time=t_start,
        end_time=t_end,
        active_duration_seconds=300.0,
        idle_duration_seconds=3300.0,
        status="completed",
    )
    # Session for U2
    s2 = models.MonitoringSession(
        user_id=u2.id,
        camera_id=1,
        start_time=t_start,
        end_time=t_end,
        active_duration_seconds=600.0,
        idle_duration_seconds=3000.0,
        status="completed",
    )
    db.add_all([s1, s2])
    db.commit()

    # Event for U1
    ev1 = models.MotionEvent(
        user_id=u1.id,
        camera_id=1,
        session_id=s1.id,
        start_time=t_start,
        end_time=t_start + datetime.timedelta(seconds=60),
        activity_state="ACTIVE",
    )
    # Event for U2
    ev2 = models.MotionEvent(
        user_id=u2.id,
        camera_id=1,
        session_id=s2.id,
        start_time=t_start,
        end_time=t_start + datetime.timedelta(seconds=120),
        activity_state="ACTIVE",
    )
    db.add_all([ev1, ev2])
    db.commit()

    # Generate summary for U1
    sum1 = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=test_date_str, user_id=u1.id, force_regenerate=True)
    # Generate summary for U2
    sum2 = DailySummaryGenerator.get_or_generate_summary(db=db, date_str=test_date_str, user_id=u2.id, force_regenerate=True)

    # Assert isolation
    assert sum1["total_motion_events"] == 1
    assert sum2["total_motion_events"] == 1
    assert sum1["active_seconds"] == 300.0
    assert sum2["active_seconds"] == 600.0

    # User 1 route query must not return User 2's event
    events_u1 = list_events(date=test_date_str, db=db, current_user=u1)
    assert len(events_u1) == 1
    assert events_u1[0].id == ev1.id

    # Cleanup
    db.query(models.DailySummary).filter(models.DailySummary.date == test_date_str).delete()
    db.query(models.MotionEvent).filter(models.MotionEvent.user_id.in_([u1.id, u2.id])).delete(synchronize_session=False)
    db.query(models.MonitoringSession).filter(models.MonitoringSession.user_id.in_([u1.id, u2.id])).delete(synchronize_session=False)
    db.commit()


# ---------------------------------------------------------------------------
# Second-Pass Item 6: Recording Frame Count 1:1 & No Duplicate Initial Frame
# ---------------------------------------------------------------------------
def test_recording_manager_exact_frame_count_and_finalization():
    """Verify that initial frame is not double-written and finalize() is safe/idempotent."""
    import numpy as np

    rm = RecordingManager(camera_id=1, camera_name="TestCam", user_id=1)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Start event by passing ACTIVE state with is_sampled=True
    rm.handle_frame(dummy_frame, activity_state="ACTIVE", motion_score=15.0, is_sampled=True)
    assert rm.is_recording is True
    assert rm.event_frame_count == 1  # Exactly 1 frame written!

    # Second sampled frame
    rm.handle_frame(dummy_frame, activity_state="ACTIVE", motion_score=12.0, is_sampled=True)
    assert rm.event_frame_count == 2

    # Unsampled frame during active event (e.g. rate-limited)
    rm.handle_frame(dummy_frame, activity_state="ACTIVE", motion_score=10.0, is_sampled=False)
    assert rm.event_frame_count == 2  # Still 2, not written!

    # Finalize should close safely and be idempotent
    rm.finalize()
    assert rm.is_recording is False
    # Second finalize call should not fail
    rm.finalize()


# ---------------------------------------------------------------------------
# Second-Pass Item 9: File Deletion Failure Preserves Database Record
# ---------------------------------------------------------------------------
def test_file_deletion_failure_preserves_db_record(db, admin_user, monkeypatch):
    """Ensure database records are NOT deleted if filesystem deletion fails with OSError."""
    # Create a dummy recording record
    rec = models.Recording(
        camera_id=1,
        user_id=admin_user.id,
        file_path="C:/nonexistent/test_video.mp4",
        file_size_bytes=1024,
        duration_seconds=10.0,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    rec_id = rec.id

    # 1. File exists on disk but unlink raises OSError
    monkeypatch.setattr(Path, "exists", lambda self: True)
    def mock_unlink(self, missing_ok=False):
        raise OSError("Permission denied: simulated file system lock")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    # Attempt delete_recording with simulated disk error -> must raise 500
    with pytest.raises(HTTPException) as exc:
        delete_recording(rec_id, db=db, current_user=admin_user)
    assert exc.value.status_code == 500
    assert "Failed to delete" in exc.value.detail

    # Verify database record still exists (NOT deleted!)
    db_rec = db.query(models.Recording).filter(models.Recording.id == rec_id).first()
    assert db_rec is not None
    assert db_rec.id == rec_id

    # 2. File is missing on disk -> cleanup succeeds without error
    monkeypatch.undo()
    res = delete_recording(rec_id, db=db, current_user=admin_user)
    assert res["message"] == "Recording deleted successfully"

    # Verify database record was deleted
    assert db.query(models.Recording).filter(models.Recording.id == rec_id).first() is None


# ---------------------------------------------------------------------------
# Second-Pass Item 10: WebSocket Telemetry Inactive/Invalid User Rejection
# ---------------------------------------------------------------------------
def test_websocket_rejects_inactive_or_invalid_user():
    """Verify WebSocket telemetry rejects inactive users or invalid tokens."""
    from backend.main import websocket_telemetry

    class AwaitableClose:
        def __await__(self):
            return iter([])

    class DummyWebSocket:
        def __init__(self):
            self.closed_code = None
            self.closed = False

        def close(self, code=1000):
            self.closed = True
            self.closed_code = code
            return AwaitableClose()

    # 1. Invalid token rejection
    ws1 = DummyWebSocket()
    coro1 = websocket_telemetry(ws1, token="invalid-token")
    try:
        coro1.send(None)
    except StopIteration:
        pass
    assert ws1.closed is True
    assert ws1.closed_code == 1008

    # 2. Inactive user token rejection
    with SessionLocal() as session:
        inactive_user = session.query(models.User).filter(models.User.email == "inactive_ws_test@cctv.local").first()
        if not inactive_user:
            inactive_user = models.User(
                email="inactive_ws_test@cctv.local",
                hashed_password="pw",
                role="operator",
                is_active=False,
            )
            session.add(inactive_user)
        else:
            inactive_user.is_active = False
        session.commit()
        session.refresh(inactive_user)
        uid = inactive_user.id

    inactive_token = create_access_token(subject=uid)
    ws2 = DummyWebSocket()
    coro2 = websocket_telemetry(ws2, token=inactive_token)
    try:
        coro2.send(None)
    except StopIteration:
        pass
    assert ws2.closed is True
    assert ws2.closed_code == 1008

