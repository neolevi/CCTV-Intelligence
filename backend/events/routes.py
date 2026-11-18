"""Motion events endpoints."""
import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user, get_current_user_flexible

router = APIRouter(prefix="/api/events", tags=["Motion Events"])


@router.get("", response_model=List[schemas.MotionEventOut])
def list_events(
    skip: int = 0,
    limit: int = 50,
    date: Optional[str] = None,
    activity_state: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List detected motion events with date, state, and keyword filtering scoped to authorization."""
    query = db.query(models.MotionEvent)

    if current_user.role != "admin":
        query = query.filter(models.MotionEvent.user_id == current_user.id)

    if date:
        try:
            d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            start = datetime.datetime.combine(d, datetime.time.min)
            end = datetime.datetime.combine(d, datetime.time.max)
            query = query.filter(models.MotionEvent.start_time >= start, models.MotionEvent.start_time <= end)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Expected YYYY-MM-DD",
            )

    if activity_state:
        query = query.filter(models.MotionEvent.activity_state == activity_state.upper())

    if search:
        query = query.filter(models.MotionEvent.description.ilike(f"%{search}%"))

    events = query.order_by(models.MotionEvent.start_time.desc()).offset(skip).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=schemas.MotionEventDetail)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve event details with all correlated sampled frames."""
    event = db.query(models.MotionEvent).filter(models.MotionEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if current_user.role != "admin" and event.user_id and event.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this event")

    frames = (
        db.query(models.CapturedFrame)
        .filter(models.CapturedFrame.event_id == event_id)
        .order_by(models.CapturedFrame.timestamp.asc())
        .all()
    )

    return {
        "id": event.id,
        "camera_id": event.camera_id,
        "session_id": event.session_id,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "peak_motion_score": event.peak_motion_score,
        "activity_state": event.activity_state,
        "frame_count": event.frame_count,
        "thumbnail_path": event.thumbnail_path,
        "description": event.description,
        "frames": frames,
    }


@router.get("/{event_id}/thumbnail")
def get_event_thumbnail(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Stream the thumbnail image for an event with authentication."""
    event = db.query(models.MotionEvent).filter(models.MotionEvent.id == event_id).first()
    if not event or not event.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    if current_user.role != "admin" and event.user_id and event.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this event")

    if event.thumbnail_path:
        p = Path(event.thumbnail_path)
        if p.exists():
            return FileResponse(path=str(p), media_type="image/jpeg")

    # Fallback to first captured frame if thumbnail file is missing
    first_frame = (
        db.query(models.CapturedFrame)
        .filter(models.CapturedFrame.event_id == event_id)
        .order_by(models.CapturedFrame.timestamp.asc())
        .first()
    )
    if first_frame and first_frame.file_path:
        fp = Path(first_frame.file_path)
        if fp.exists():
            return FileResponse(path=str(fp), media_type="image/jpeg")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file missing on disk")


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a motion event, thumbnail, and associated database records."""
    event = db.query(models.MotionEvent).filter(models.MotionEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if current_user.role != "admin" and event.user_id and event.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to delete this event")

    if event.thumbnail_path:
        p = Path(event.thumbnail_path)
        if p.exists():
            try:
                p.unlink()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete event thumbnail from storage: {e}",
                )

    db.delete(event)
    db.commit()
    return {"message": "Event deleted successfully"}
