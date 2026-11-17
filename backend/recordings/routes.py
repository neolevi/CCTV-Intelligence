"""Video recordings management and streaming endpoints."""
import datetime
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user, get_current_user_flexible

router = APIRouter(prefix="/api/recordings", tags=["Video Recordings"])


@router.get("", response_model=List[schemas.RecordingOut])
def list_recordings(
    skip: int = 0,
    limit: int = 50,
    date: Optional[str] = None,
    activity_state: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List available surveillance video recordings scoped to user authorization."""
    query = db.query(models.Recording)

    # User authorization: non-admins only see recordings they own or default system recordings
    if current_user.role != "admin":
        query = query.filter((models.Recording.user_id == current_user.id) | (models.Recording.user_id == None))

    if date:
        try:
            d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            start = datetime.datetime.combine(d, datetime.time.min)
            end = datetime.datetime.combine(d, datetime.time.max)
            query = query.filter(models.Recording.start_time >= start, models.Recording.start_time <= end)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Expected YYYY-MM-DD",
            )

    if activity_state:
        query = query.filter(models.Recording.activity_state == activity_state.upper())

    recordings = query.order_by(models.Recording.start_time.desc()).offset(skip).limit(limit).all()
    return recordings


@router.get("/{recording_id}", response_model=schemas.RecordingOut)
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve metadata for a specific video recording."""
    rec = db.query(models.Recording).filter(models.Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    if current_user.role != "admin" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this recording")

    return rec


@router.get("/{recording_id}/stream")
def stream_recording_video(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Stream recording video for direct in-browser HTML5 video playback with authentication."""
    rec = db.query(models.Recording).filter(models.Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    if current_user.role != "admin" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this recording")

    p = Path(rec.file_path)
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing from disk")

    media_type = "video/mp4" if p.suffix.lower() == ".mp4" else "video/x-msvideo"
    return FileResponse(path=str(p), media_type=media_type)


@router.get("/{recording_id}/download")
def download_recording_video(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Download the raw video recording file."""
    rec = db.query(models.Recording).filter(models.Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    if current_user.role != "admin" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this recording")

    p = Path(rec.file_path)
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing from disk")

    return FileResponse(
        path=str(p),
        media_type="application/octet-stream",
        filename=p.name,
    )


@router.get("/{recording_id}/thumbnail")
def get_recording_thumbnail(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Serve thumbnail image for the recording with authentication."""
    rec = db.query(models.Recording).filter(models.Recording.id == recording_id).first()
    if not rec or not rec.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    if current_user.role != "admin" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this recording")

    p = Path(rec.thumbnail_path)
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file missing on disk")

    return FileResponse(path=str(p), media_type="image/jpeg")


@router.delete("/{recording_id}")
def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete video recording file from disk and database record."""
    rec = db.query(models.Recording).filter(models.Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")

    if current_user.role != "admin" and rec.user_id and rec.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to delete this recording")

    # Remove video file
    try:
        p = Path(rec.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass

    # Remove thumbnail
    if rec.thumbnail_path:
        try:
            tp = Path(rec.thumbnail_path)
            if tp.exists():
                tp.unlink()
        except Exception:
            pass

    db.delete(rec)
    db.commit()
    return {"message": "Recording deleted successfully"}
