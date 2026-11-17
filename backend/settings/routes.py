"""System settings management endpoints."""
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user
from backend.config import settings
from vision.camera_manager import camera_manager

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=schemas.SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve full application settings and physical disk usage."""
    # Read key-value settings from DB
    records = db.query(models.SystemSetting).all()
    s_map = {r.key: r.value for r in records}

    # Query storage disk metrics
    storage_path = str(settings.STORAGE_DIR)
    total, used, free = shutil.disk_usage(storage_path)

    return {
        "motion_sensitivity": int(s_map.get("motion_sensitivity", settings.MOTION_SENSITIVITY)),
        "motion_threshold_percent": float(s_map.get("motion_threshold_percent", settings.MOTION_THRESHOLD_PERCENT)),
        "idle_timeout_seconds": float(s_map.get("idle_timeout_seconds", settings.IDLE_TIMEOUT_SECONDS)),
        "deep_idle_timeout_seconds": float(s_map.get("deep_idle_timeout_seconds", settings.DEEP_IDLE_TIMEOUT_SECONDS)),
        "active_sampling_fps": float(s_map.get("active_sampling_fps", settings.ACTIVE_SAMPLING_FPS)),
        "idle_sampling_fps": float(s_map.get("idle_sampling_fps", settings.IDLE_SAMPLING_FPS)),
        "deep_idle_sampling_fps": float(s_map.get("deep_idle_sampling_fps", settings.DEEP_IDLE_SAMPLING_FPS)),
        "storage_retention_days": int(s_map.get("storage_retention_days", settings.STORAGE_RETENTION_DAYS)),
        "theme": s_map.get("theme", "dark"),
        "default_camera_index": settings.DEFAULT_CAMERA_INDEX,
        "resolution_width": settings.DEFAULT_FRAME_WIDTH,
        "resolution_height": settings.DEFAULT_FRAME_HEIGHT,
        "storage_path": storage_path,
        "storage_used_bytes": used,
        "storage_free_bytes": free,
    }


@router.put("", response_model=schemas.SettingsOut)
def update_settings(
    update_data: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update settings, persist to DB, and apply dynamically to active vision modules."""
    data_dict = update_data.model_dump(exclude_unset=True)

    for key, val in data_dict.items():
        if val is None:
            continue
        rec = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
        if not rec:
            rec = models.SystemSetting(key=key, value=str(val))
            db.add(rec)
        else:
            rec.value = str(val)

    db.commit()

    # Dynamically apply changes to running vision engine
    camera_manager.motion_detector.update_settings(
        sensitivity=update_data.motion_sensitivity,
        motion_threshold_percent=update_data.motion_threshold_percent,
        idle_timeout=update_data.idle_timeout_seconds,
        deep_idle_timeout=update_data.deep_idle_timeout_seconds,
    )
    camera_manager.adaptive_sampler.update_rates(
        active_fps=update_data.active_sampling_fps,
        idle_fps=update_data.idle_sampling_fps,
        deep_idle_fps=update_data.deep_idle_sampling_fps,
    )

    return get_settings(db=db, current_user=current_user)
