"""Recording manager for handling video clips, captured frames, and database event logging."""
import datetime
import os
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import cv2
import numpy as np

from backend.config import settings
from backend.database import SessionLocal
from backend import models
from vision.frame_processor import FrameProcessor


class RecordingManager:
    """
    Coordinates frame saving, event clustering, thumbnail generation,
    and video file recording (using OpenCV VideoWriter).
    """

    def __init__(self, camera_id: int, camera_name: str, user_id: Optional[int] = None):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.user_id = user_id

        self.current_event_id: Optional[int] = None
        self.current_session_id: Optional[int] = None
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_video_path: Optional[Path] = None
        self.event_start_time: Optional[datetime.datetime] = None
        self.peak_motion_score: float = 0.0
        self.event_frame_count: int = 0
        self.event_thumbnail_path: Optional[str] = None
        self.frame_width: int = settings.DEFAULT_FRAME_WIDTH
        self.frame_height: int = settings.DEFAULT_FRAME_HEIGHT
        self.recording_fps: float = float(settings.ACTIVE_SAMPLING_FPS)
        self._lock = threading.Lock()
        self._finalized = False

    @property
    def is_recording(self) -> bool:
        """Returns True if a motion event recording is currently open."""
        return self.current_event_id is not None

    def set_session_id(self, session_id: Optional[int]) -> None:
        """Assign current active monitoring session ID."""
        self.current_session_id = session_id

    def handle_frame(
        self,
        frame: np.ndarray,
        activity_state: str,
        motion_score: float,
        is_sampled: bool,
    ) -> None:
        """
        Processes an incoming frame in real-time surveillance:
        - If state is ACTIVE, initiates or appends to a motion event & video recording.
        - Frame is written to the video writer according to the adaptive sampling rate.
        - If state transitioned away from ACTIVE, finalizes the open recording event.
        - If is_sampled is True, saves the frame as an individual captured frame asset.
        """
        with self._lock:
            if self._finalized:
                return

            now_dt = datetime.datetime.now()
            date_str = now_dt.strftime("%Y-%m-%d")

            # 1. State is ACTIVE -> ensure event and video writer are started
            if activity_state == "ACTIVE":
                if self.current_event_id is None:
                    self._start_event(frame, motion_score, now_dt, date_str)
                else:
                    self.peak_motion_score = max(self.peak_motion_score, motion_score)

                # Write frame to video recording exactly once when sampled
                if is_sampled and self.video_writer is not None and self.video_writer.isOpened():
                    self.video_writer.write(frame)
                    self.event_frame_count += 1

            # 2. State is not ACTIVE, but we had an ongoing event -> close it
            elif self.current_event_id is not None:
                self._close_event(now_dt)

            # 3. If this frame is selected by adaptive sampler, persist captured frame
            if is_sampled:
                self._save_captured_frame(frame, activity_state, motion_score, now_dt, date_str)

    def _start_event(
        self,
        frame: np.ndarray,
        motion_score: float,
        now_dt: datetime.datetime,
        date_str: str,
    ) -> None:
        """Start a new motion event and open VideoWriter."""
        self.event_start_time = now_dt
        self.peak_motion_score = motion_score
        self.event_frame_count = 0

        h, w = frame.shape[:2]
        self.frame_width = w
        self.frame_height = h

        # Create event directory
        rec_dir = settings.RECORDINGS_DIR / date_str
        rec_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir = settings.THUMBNAILS_DIR / date_str
        thumb_dir.mkdir(parents=True, exist_ok=True)

        # Create MotionEvent row in SQLite
        with SessionLocal() as db:
            event = models.MotionEvent(
                user_id=self.user_id,
                camera_id=self.camera_id,
                session_id=self.current_session_id,
                start_time=now_dt,
                peak_motion_score=motion_score,
                activity_state="ACTIVE",
                frame_count=0,
                description=f"Motion detected on {self.camera_name}",
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            self.current_event_id = event.id

        # Generate thumbnail
        thumb_filename = f"thumb_event_{self.current_event_id}_{now_dt.strftime('%H%M%S')}.jpg"
        thumb_path = thumb_dir / thumb_filename
        FrameProcessor.generate_thumbnail(frame, thumb_path)
        self.event_thumbnail_path = str(thumb_path)

        # Update event with thumbnail path
        with SessionLocal() as db:
            ev = db.query(models.MotionEvent).filter(models.MotionEvent.id == self.current_event_id).first()
            if ev:
                ev.thumbnail_path = self.event_thumbnail_path
                db.commit()

        # Initialize VideoWriter
        # Use mp4v or fallback to XVID
        video_filename = f"rec_{self.current_event_id}_{now_dt.strftime('%H%M%S')}.mp4"
        self.current_video_path = rec_dir / video_filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(
            str(self.current_video_path),
            fourcc,
            self.recording_fps,
            (w, h),
        )

        if not self.video_writer.isOpened():
            # Fallback codec
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            self.current_video_path = rec_dir / f"rec_{self.current_event_id}_{now_dt.strftime('%H%M%S')}.avi"
            self.video_writer = cv2.VideoWriter(
                str(self.current_video_path),
                fourcc,
                self.recording_fps,
                (w, h),
            )

        self.event_frame_count = 0

    def _close_event(self, end_dt: datetime.datetime) -> None:
        """Close current active event, finalize video, and write Recording record."""
        if self.current_event_id is None:
            return

        # Release video writer
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

        file_size_bytes = 0
        if self.current_video_path and self.current_video_path.exists():
            file_size_bytes = self.current_video_path.stat().st_size

        duration_seconds = 0.0
        if self.event_start_time:
            duration_seconds = max(0.1, (end_dt - self.event_start_time).total_seconds())

        # Update DB MotionEvent
        with SessionLocal() as db:
            ev = db.query(models.MotionEvent).filter(models.MotionEvent.id == self.current_event_id).first()
            if ev:
                ev.end_time = end_dt
                ev.frame_count = self.event_frame_count
                ev.peak_motion_score = self.peak_motion_score

            # Insert Recording record only when actual frames were captured
            if self.event_frame_count > 0 and self.current_video_path and self.current_video_path.exists():
                recording = models.Recording(
                    user_id=self.user_id,
                    camera_id=self.camera_id,
                    session_id=self.current_session_id,
                    event_id=self.current_event_id,
                    start_time=self.event_start_time or end_dt,
                    end_time=end_dt,
                    duration_seconds=round(duration_seconds, 2),
                    file_path=str(self.current_video_path),
                    file_size_bytes=file_size_bytes,
                    thumbnail_path=self.event_thumbnail_path,
                    activity_state="ACTIVE",
                )
                db.add(recording)
            elif self.event_frame_count == 0 and self.current_video_path and self.current_video_path.exists():
                try:
                    self.current_video_path.unlink()
                except Exception:
                    pass

            db.commit()

        # Reset event tracking
        self.current_event_id = None
        self.current_video_path = None
        self.event_start_time = None
        self.event_frame_count = 0
        self.event_thumbnail_path = None
        self.peak_motion_score = 0.0

    def _save_captured_frame(
        self,
        frame: np.ndarray,
        activity_state: str,
        motion_score: float,
        now_dt: datetime.datetime,
        date_str: str,
    ) -> None:
        """Save a single keyframe to storage and create DB entry."""
        frame_dir = settings.FRAMES_DIR / date_str
        frame_dir.mkdir(parents=True, exist_ok=True)

        filename = f"frame_{now_dt.strftime('%H%M%S_%f')}_{activity_state.lower()}.jpg"
        file_path = frame_dir / filename

        # Annotate HUD overlay on saved frame for evidence review
        annotated = FrameProcessor.add_overlay(
            frame=frame,
            camera_name=self.camera_name,
            activity_state=activity_state,
            motion_score=motion_score,
            timestamp=now_dt,
        )
        FrameProcessor.save_frame(annotated, file_path)

        file_size_bytes = 0
        if file_path.exists():
            try:
                file_size_bytes = file_path.stat().st_size
            except Exception:
                pass

        with SessionLocal() as db:
            cf = models.CapturedFrame(
                user_id=self.user_id,
                camera_id=self.camera_id,
                session_id=self.current_session_id,
                event_id=self.current_event_id,
                timestamp=now_dt,
                activity_state=activity_state,
                file_path=str(file_path),
                file_size_bytes=file_size_bytes,
                motion_score=motion_score,
            )
            db.add(cf)
            db.commit()

    def finalize(self) -> None:
        """Flush and finalize any pending recordings on shutdown."""
        with self._lock:
            if not self._finalized:
                self._finalized = True
                if self.current_event_id is not None:
                    self._close_event(datetime.datetime.now())
