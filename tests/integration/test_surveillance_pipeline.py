"""End-to-End Integration Test for CCTV Intelligence Surveillance Pipeline."""
import time
from pathlib import Path
import pytest
from vision.camera_manager import camera_manager
from backend.database import SessionLocal
from backend import models
from backend.cameras.routes import start_camera, stop_camera, trigger_simulated_motion, StartMonitoringRequest, TriggerMotionRequest
from backend.recordings.routes import list_recordings
from backend.events.routes import list_events
from backend.summaries.routes import get_daily_summary


def test_end_to_end_surveillance_pipeline():
    with SessionLocal() as db:
        admin = db.query(models.User).filter(models.User.email == "admin@cctv.local").first()
        assert admin is not None

        # 1. Start Monitoring with Virtual Sensor (device_index = -1)
        req = StartMonitoringRequest(camera_id=1, device_index=-1)
        start_res = start_camera(req, current_user=admin, db=db)
        assert camera_manager.is_monitoring is True

        # 2. Inject simulated motion to force ACTIVE state
        trig_req = TriggerMotionRequest(active=True)
        trigger_simulated_motion(trig_req, current_user=admin)

        # Let pipeline execute and record frames
        time.sleep(1.2)

        # Check status during active motion
        status = camera_manager.get_status()
        assert status["total_frames_processed"] > 0

        # 3. Reset motion to allow event to close and video file to finalize
        reset_req = TriggerMotionRequest(active=False)
        trigger_simulated_motion(reset_req, current_user=admin)
        time.sleep(0.5)

        # 4. Stop monitoring
        stop_res = stop_camera(current_user=admin)
        assert camera_manager.is_monitoring is False

        # 5. Verify Events and Recordings in Database
        events = db.query(models.MotionEvent).order_by(models.MotionEvent.id.asc()).all()
        assert len(events) > 0
        latest_event = events[-1]
        assert latest_event.peak_motion_score >= 0.0

        recordings = db.query(models.Recording).all()
        assert len(recordings) > 0
        latest_rec = recordings[-1]
        assert Path(latest_rec.file_path).exists()
        assert latest_rec.file_size_bytes > 0

        # 6. Verify Recordings route returns recording
        recs = list_recordings(db=db, current_user=admin)
        assert len(recs) > 0

        # 7. Verify Events route returns event
        evs = list_events(db=db, current_user=admin)
        assert len(evs) > 0

        # 8. Verify Daily Summary integrates the new surveillance records
        summary = get_daily_summary(db=db, current_user=admin)
        assert summary["total_motion_events"] > 0
        assert "motion event" in summary["narrative_summary"].lower()
