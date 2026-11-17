"""Tests for Core CCTV Intelligence API Endpoint Functions."""
import pytest
from backend.database import SessionLocal
from backend import models, schemas
from backend.main import health_check
from backend.cameras.routes import (
    get_camera_devices,
    get_camera_status,
    start_camera,
    stop_camera,
    trigger_simulated_motion,
    StartMonitoringRequest,
    TriggerMotionRequest,
)
from backend.motion.routes import get_motion_status, get_motion_statistics
from backend.settings.routes import get_settings, update_settings
from backend.analytics.routes import get_analytics_overview, get_analytics_trends


@pytest.fixture(scope="module")
def admin_user():
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        return admin


def test_health_endpoint():
    res = health_check()
    assert res["status"] == "healthy"
    assert res["app"] == "CCTV Intelligence"


def test_camera_devices_and_status():
    devs = get_camera_devices()
    assert isinstance(devs, list)
    assert len(devs) > 0

    status = get_camera_status()
    assert "activity_state" in status
    assert "current_fps" in status


def test_camera_start_stop_and_motion(admin_user):
    with SessionLocal() as db:
        # Start virtual camera
        req = StartMonitoringRequest(camera_id=1, device_index=-1)
        start_res = start_camera(req, current_user=admin_user, db=db)
        assert start_res["status"]["is_monitoring"] is True

        # Check motion status
        m_status = get_motion_status()
        assert "motion_score" in m_status

        # Trigger simulated motion
        trig_req = TriggerMotionRequest(active=True)
        trig_res = trigger_simulated_motion(trig_req, current_user=admin_user)
        assert "Simulated motion set to True" in trig_res["message"]

        # Stop camera
        stop_res = stop_camera(current_user=admin_user)
        assert stop_res["status"]["is_monitoring"] is False


def test_motion_statistics(admin_user):
    with SessionLocal() as db:
        stats = get_motion_statistics(db=db, current_user=admin_user)
        assert "active_percentage" in stats
        assert "total_events_today" in stats


def test_settings_endpoints(admin_user):
    with SessionLocal() as db:
        s = get_settings(db=db, current_user=admin_user)
        assert s["motion_sensitivity"] > 0
        assert s["active_sampling_fps"] > 0

        # Update settings
        up_data = schemas.SettingsUpdate(
            motion_sensitivity=28,
            active_sampling_fps=6.0,
        )
        updated = update_settings(up_data, db=db, current_user=admin_user)
        assert updated["motion_sensitivity"] == 28
        assert updated["active_sampling_fps"] == 6.0


def test_analytics_endpoints(admin_user):
    with SessionLocal() as db:
        ov = get_analytics_overview(db=db, current_user=admin_user)
        assert "today_active_seconds" in ov
        assert "total_storage_used_bytes" in ov

        tr = get_analytics_trends(days=7, db=db, current_user=admin_user)
        assert len(tr["dates"]) == 7
        assert len(tr["motion_event_counts"]) == 7
