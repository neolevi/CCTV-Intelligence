"""Motion detection telemetry and analytics endpoints."""
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user
from vision.camera_manager import camera_manager

router = APIRouter(prefix="/api/motion", tags=["Motion Detection"])


@router.get("/status", response_model=schemas.MotionStatusOut)
def get_motion_status():
    """Retrieve instantaneous motion detection state and score."""
    status = camera_manager.get_status()
    motion_det = camera_manager.motion_detector.get_status()

    return {
        "activity_state": motion_det["activity_state"],
        "motion_score": motion_det["motion_score"],
        "is_motion_detected": motion_det["is_motion_detected"],
        "sampling_fps": status["sampling_fps"],
        "time_in_current_state": motion_det["time_in_current_state"],
        "active_timeout_remaining": motion_det["active_timeout_remaining"],
    }


@router.get("/statistics", response_model=schemas.MotionStatisticsOut)
def get_motion_statistics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Calculate today's motion and activity state distribution."""
    today_start = datetime.datetime.combine(datetime.datetime.now().date(), datetime.time.min)
    today_end = datetime.datetime.combine(datetime.datetime.now().date(), datetime.time.max)

    # Query today's events
    events = (
        db.query(models.MotionEvent)
        .filter(models.MotionEvent.start_time >= today_start, models.MotionEvent.start_time <= today_end)
        .all()
    )

    total_events = len(events)
    peak_score = max((e.peak_motion_score or 0.0 for e in events), default=0.0)

    # Durations from active sessions today
    status = camera_manager.get_status()
    active_sec = status["active_seconds"]
    idle_sec = status["idle_seconds"]
    deep_idle_sec = status["deep_idle_seconds"]
    total_sec = active_sec + idle_sec + deep_idle_sec

    if total_sec > 0:
        active_pct = round((active_sec / total_sec) * 100.0, 1)
        idle_pct = round((idle_sec / total_sec) * 100.0, 1)
        deep_idle_pct = round((deep_idle_sec / total_sec) * 100.0, 1)
    else:
        active_pct = 0.0
        idle_pct = 100.0
        deep_idle_pct = 0.0

    return {
        "active_percentage": active_pct,
        "idle_percentage": idle_pct,
        "deep_idle_percentage": deep_idle_pct,
        "total_events_today": total_events,
        "peak_motion_score_today": round(peak_score, 2),
    }
