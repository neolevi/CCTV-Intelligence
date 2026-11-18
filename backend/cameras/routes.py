"""Camera management and live MJPEG streaming routes."""
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth.routes import get_current_user, get_current_user_flexible
from vision.camera_manager import camera_manager

router = APIRouter(prefix="/api/camera", tags=["Camera Management"])


class StartMonitoringRequest(BaseModel):
    camera_id: Optional[int] = 1
    device_index: Optional[int] = 0
    rtsp_url: Optional[str] = None


class TriggerMotionRequest(BaseModel):
    active: bool = True


@router.get("/devices", response_model=List[schemas.CameraDeviceOption])
def get_camera_devices(
    current_user: models.User = Depends(get_current_user),
):
    """Enumerate hardware webcam devices and virtual surveillance cameras."""
    return camera_manager.list_devices()


@router.get("/status", response_model=schemas.CameraStatusOut)
def get_camera_status(
    current_user: models.User = Depends(get_current_user),
):
    """Retrieve real-time camera connection and monitoring status."""
    return camera_manager.get_status()


@router.post("/start")
def start_camera(
    req: StartMonitoringRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start live surveillance monitoring pipeline."""
    # 1. Resolve requested camera and verify ownership
    cam_id = req.camera_id or 1
    cam = db.query(models.Camera).filter(models.Camera.id == cam_id).first()
    if not cam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera #{cam_id} not found.",
        )

    if current_user.role != "admin" and cam.user_id is not None and cam.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to operate this camera.",
        )

    # 2. Check if a monitoring session is already active (resolve multi-user / singleton concurrency)
    if camera_manager.is_monitoring:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A camera monitoring session is already active (Camera #{camera_manager.camera_id}). Please stop it before starting another.",
        )

    try:
        success = camera_manager.start_monitoring(
            camera_id=cam_id,
            device_index=req.device_index if req.device_index is not None else 0,
            rtsp_url=req.rtsp_url,
            user_id=current_user.id,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate camera monitoring.",
        )
    return {"message": "Camera monitoring started successfully.", "status": camera_manager.get_status()}


@router.post("/stop")
def stop_camera(
    current_user: models.User = Depends(get_current_user),
):
    """Stop surveillance monitoring and release hardware camera resources."""
    # Prevent stopping another user's session
    if camera_manager.is_monitoring:
        if (
            camera_manager.user_id is not None
            and current_user.role != "admin"
            and camera_manager.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot stop another operator's active monitoring session.",
            )

    stopped = camera_manager.stop_monitoring()
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Camera monitoring thread did not terminate cleanly.",
        )
    return {"message": "Camera monitoring stopped.", "status": camera_manager.get_status()}


@router.post("/trigger_motion")
def trigger_simulated_motion(
    req: TriggerMotionRequest,
    current_user: models.User = Depends(get_current_user),
):
    """Trigger or reset simulated motion for interactive testing."""
    camera_manager.trigger_simulated_motion(req.active)
    return {"message": f"Simulated motion set to {req.active}", "status": camera_manager.get_status()}


def _generate_mjpeg_stream():
    """Generator yielding multipart JPEG frames for live surveillance streaming."""
    while camera_manager.is_monitoring:
        frame_bytes = camera_manager.get_latest_jpeg()
        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
        time.sleep(0.04)  # ~25 FPS stream delivery


@router.get("/stream")
def stream_live_video(
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Stream live CCTV surveillance video via multipart/x-mixed-replace MJPEG with authentication."""
    # Prevent automatic virtual camera start. Return standby frame if inactive.
    if not camera_manager.is_monitoring:
        standby_bytes = camera_manager.get_standby_jpeg()
        return Response(content=standby_bytes, media_type="image/jpeg")

    # Prevent access to another user's live stream
    if (
        camera_manager.user_id is not None
        and current_user.role != "admin"
        and camera_manager.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view another operator's live camera stream.",
        )

    return StreamingResponse(
        _generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
