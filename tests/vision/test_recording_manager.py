"""Tests for Recording Manager and video/frame persistence."""
import datetime
from pathlib import Path
import numpy as np
import pytest
from vision.recording_manager import RecordingManager
from backend.database import SessionLocal
from backend import models


def test_recording_manager_event_flow():
    mgr = RecordingManager(camera_id=1, camera_name="Test Cam")
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # 1. First active frame opens event
    mgr.handle_frame(
        frame=frame,
        activity_state="ACTIVE",
        motion_score=4.2,
        is_sampled=True,
    )
    event_id = mgr.current_event_id
    assert event_id is not None
    assert mgr.video_writer is not None

    # Check DB event record
    with SessionLocal() as db:
        ev = db.query(models.MotionEvent).filter(models.MotionEvent.id == event_id).first()
        assert ev is not None
        assert ev.activity_state == "ACTIVE"

    # 2. Append additional active frames
    for _ in range(3):
        mgr.handle_frame(
            frame=frame,
            activity_state="ACTIVE",
            motion_score=5.0,
            is_sampled=False,
        )

    # 3. Transition to IDLE closes event and writes recording
    mgr.handle_frame(
        frame=frame,
        activity_state="IDLE",
        motion_score=0.2,
        is_sampled=False,
    )

    assert mgr.current_event_id is None
    assert mgr.video_writer is None

    # Verify Recording record was created in SQLite
    with SessionLocal() as db:
        rec = db.query(models.Recording).filter(models.Recording.event_id == event_id).first()
        assert rec is not None
        assert Path(rec.file_path).exists()
        assert rec.file_size_bytes > 0
