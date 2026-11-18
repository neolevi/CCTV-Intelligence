"""Captured surveillance frames endpoints."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user, get_current_user_flexible

router = APIRouter(prefix="/api/frames", tags=["Captured Frames"])


@router.get("", response_model=List[schemas.CapturedFrameOut])
def list_frames(
    skip: int = 0,
    limit: int = 50,
    activity_state: Optional[str] = None,
    event_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve saved surveillance frames scoped to authorization."""
    query = db.query(models.CapturedFrame)

    if current_user.role != "admin":
        query = query.filter(models.CapturedFrame.user_id == current_user.id)

    if activity_state:
        query = query.filter(models.CapturedFrame.activity_state == activity_state.upper())
    if event_id:
        query = query.filter(models.CapturedFrame.event_id == event_id)

    frames = query.order_by(models.CapturedFrame.timestamp.desc()).offset(skip).limit(limit).all()
    return frames


@router.get("/{frame_id}", response_model=schemas.CapturedFrameOut)
def get_frame(
    frame_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve metadata for a specific frame."""
    frame = db.query(models.CapturedFrame).filter(models.CapturedFrame.id == frame_id).first()
    if not frame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")

    if current_user.role != "admin" and frame.user_id and frame.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this frame")

    return frame


@router.get("/{frame_id}/image")
def get_frame_image(
    frame_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Return the raw JPEG image for a captured frame with authentication."""
    frame = db.query(models.CapturedFrame).filter(models.CapturedFrame.id == frame_id).first()
    if not frame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")

    if current_user.role != "admin" and frame.user_id and frame.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this frame")

    p = Path(frame.file_path)
    if not p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame image file missing from disk")

    return FileResponse(path=str(p), media_type="image/jpeg")


@router.delete("/{frame_id}")
def delete_frame(
    frame_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a captured frame record and remove the file from storage."""
    frame = db.query(models.CapturedFrame).filter(models.CapturedFrame.id == frame_id).first()
    if not frame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")

    if current_user.role != "admin" and frame.user_id and frame.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to delete this frame")

    if frame.file_path:
        p = Path(frame.file_path)
        if p.exists():
            try:
                p.unlink()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete frame image file from storage: {e}",
                )

    db.delete(frame)
    db.commit()
    return {"message": "Frame deleted successfully"}
