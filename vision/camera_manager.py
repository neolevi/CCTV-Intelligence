"""Camera Manager for device capture, streaming, motion detection, and recording coordination."""
import datetime
import math
import os
import threading
import time
from typing import Dict, Any, List, Optional
import cv2
import numpy as np

from backend.config import settings
from backend.database import SessionLocal
from backend import models
from vision.motion_detector import MotionDetector
from vision.adaptive_sampler import AdaptiveSampler
from vision.recording_manager import RecordingManager
from vision.frame_processor import FrameProcessor


class CameraManager:
    """
    Manages camera lifecycle, live video capture loop, motion detection,
    adaptive frame sampling, and recording management in a dedicated thread.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.is_monitoring: bool = False
        self.is_connected: bool = False
        self.camera_id: int = 1
        self.user_id: Optional[int] = None
        self.camera_name: str = "Main Surveillance Camera"
        self.device_index: int = 0
        self.rtsp_url: Optional[str] = None
        self.is_virtual_camera: bool = False

        # Vision components
        self.motion_detector = MotionDetector(
            var_threshold=settings.MOTION_SENSITIVITY,
            motion_threshold_percent=settings.MOTION_THRESHOLD_PERCENT,
            idle_timeout=settings.IDLE_TIMEOUT_SECONDS,
            deep_idle_timeout=settings.DEEP_IDLE_TIMEOUT_SECONDS,
            processing_width=320,
            processing_height=240,
        )
        self.adaptive_sampler = AdaptiveSampler(
            active_fps=settings.ACTIVE_SAMPLING_FPS,
            idle_fps=settings.IDLE_SAMPLING_FPS,
            deep_idle_fps=settings.DEEP_IDLE_SAMPLING_FPS,
        )
        self.recording_manager: Optional[RecordingManager] = None

        # Capture thread
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.cap: Optional[cv2.VideoCapture] = None

        # Latest frame buffer for MJPEG streaming
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.frame_lock = threading.Lock()

        # Telemetry & Statistics
        self.start_monitoring_time: Optional[float] = None
        self.session_id: Optional[int] = None
        self.total_frames_processed: int = 0
        self.total_frames_saved: int = 0
        self.active_seconds: float = 0.0
        self.idle_seconds: float = 0.0
        self.deep_idle_seconds: float = 0.0
        self.last_loop_time: float = time.monotonic()
        self.current_fps: float = 0.0

        # Virtual animation state
        self._anim_x = 50.0
        self._anim_dx = 4.0
        self._simulated_motion_active = False

    def list_devices(self) -> List[Dict[str, Any]]:
        """Probe available camera devices on the system."""
        devices = []
        # Check standard physical indices 0, 1 safely
        for idx in range(2):
            try:
                cap = cv2.VideoCapture(idx)
                if cap and cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        devices.append({
                            "index": idx,
                            "name": f"USB Video Device {idx}",
                            "is_available": True,
                        })
            except Exception:
                pass

        # Always include virtual surveillance simulation device for testing & environments without webcams
        devices.append({
            "index": -1,
            "name": "Simulated CCTV Feed (Virtual Sensor)",
            "is_available": True,
        })
        return devices

    def start_monitoring(
        self,
        camera_id: int = 1,
        device_index: int = 0,
        rtsp_url: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """Start live monitoring pipeline in a background thread."""
        with self._lock:
            if self.is_monitoring:
                return True

            self.camera_id = camera_id
            self.device_index = device_index
            self.rtsp_url = rtsp_url
            self.user_id = user_id
            self.is_virtual_camera = False

            # Query camera info from DB
            with SessionLocal() as db:
                cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
                if cam:
                    self.camera_name = cam.name

            # Hardware vs Virtual distinction (Physical cameras are strictly used without silent fallback)
            if device_index >= 0:
                try:
                    self.cap = cv2.VideoCapture(device_index)
                    if not self.cap or not self.cap.isOpened():
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                        with SessionLocal() as db:
                            cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
                            if cam:
                                cam.is_connected = False
                                cam.status = "error"
                                db.commit()
                        raise RuntimeError(f"Physical camera device {device_index} cannot be opened. Hardware unavailable.")

                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.DEFAULT_FRAME_WIDTH)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.DEFAULT_FRAME_HEIGHT)
                    self.cap.set(cv2.CAP_PROP_FPS, settings.DEFAULT_CAMERA_FPS)
                    self.is_connected = True
                    self.is_virtual_camera = False
                except Exception as e:
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                    with SessionLocal() as db:
                        cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
                        if cam:
                            cam.is_connected = False
                            cam.status = "error"
                            db.commit()
                    raise RuntimeError(f"Error connecting to physical camera device {device_index}: {e}")
            else:
                # Explicit simulated sensor mode
                self.is_virtual_camera = True
                self.is_connected = True

            with SessionLocal() as db:
                cam = db.query(models.Camera).filter(models.Camera.id == camera_id).first()
                if cam:
                    cam.is_connected = True
                    cam.status = "monitoring"
                    db.commit()

            # Create new MonitoringSession in DB
            now_dt = datetime.datetime.now()
            with SessionLocal() as db:
                session = models.MonitoringSession(
                    user_id=self.user_id,
                    camera_id=self.camera_id,
                    start_time=now_dt,
                    status="active",
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                self.session_id = session.id

            # Initialize Recording Manager
            self.recording_manager = RecordingManager(
                camera_id=self.camera_id,
                camera_name=self.camera_name,
                user_id=self.user_id,
            )
            self.recording_manager.set_session_id(self.session_id)

            # Reset telemetry
            self.stop_event.clear()
            self.start_monitoring_time = time.time()
            self.last_loop_time = time.time()
            self.total_frames_processed = 0
            self.total_frames_saved = 0
            self.active_seconds = 0.0
            self.idle_seconds = 0.0
            self.deep_idle_seconds = 0.0
            self.adaptive_sampler.reset_stats()

            # Launch capture thread
            self.is_monitoring = True
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="CameraCaptureLoop",
            )
            self.capture_thread.start()
            return True

    def stop_monitoring(self) -> bool:
        """Gracefully stop live monitoring and persist session duration."""
        with self._lock:
            if not self.is_monitoring:
                return True

            self.stop_event.set()
            thread = self.capture_thread

        # Join capture thread OUTSIDE self._lock to prevent lock deadlock
        if thread and thread.is_alive():
            thread.join(timeout=3.0)

        with self._lock:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

            if self.recording_manager:
                self.recording_manager.finalize()

            self.is_monitoring = False
            self.is_connected = False

            # Update MonitoringSession and Camera in DB
            now_dt = datetime.datetime.now()
            with SessionLocal() as db:
                if self.session_id:
                    session = db.query(models.MonitoringSession).filter(
                        models.MonitoringSession.id == self.session_id
                    ).first()
                    if session:
                        session.end_time = now_dt
                        session.status = "completed"
                        session.total_frames = self.total_frames_processed
                        session.active_duration_seconds = round(self.active_seconds, 2)
                        session.idle_duration_seconds = round(self.idle_seconds, 2)
                        session.deep_idle_duration_seconds = round(self.deep_idle_seconds, 2)

                cam = db.query(models.Camera).filter(models.Camera.id == self.camera_id).first()
                if cam:
                    cam.is_connected = False
                    cam.status = "standby"

                db.commit()

            return True

    def trigger_simulated_motion(self, active: bool = True) -> None:
        """Allows testing or manually triggering motion events on the feed."""
        self._simulated_motion_active = active

    def _generate_virtual_frame(self) -> np.ndarray:
        """
        Generate realistic simulated CCTV frame with a surveillance scene,
        timecode, ambient camera sensor noise, and moving activity objects.
        """
        w, h = settings.DEFAULT_FRAME_WIDTH, settings.DEFAULT_FRAME_HEIGHT
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Background room / hallway gradient
        for y in range(h):
            val = int(35 + (y / h) * 45)
            frame[y, :] = (val, val + 5, val + 10)

        # Draw architectural room perspective lines (hallway / doorway)
        cv2.line(frame, (0, 0), (w // 3, h // 2), (60, 65, 75), 2)
        cv2.line(frame, (w, 0), (2 * w // 3, h // 2), (60, 65, 75), 2)
        cv2.line(frame, (0, h), (w // 3, h // 2), (50, 55, 60), 2)
        cv2.line(frame, (w, h), (2 * w // 3, h // 2), (50, 55, 60), 2)
        cv2.rectangle(frame, (w // 3, h // 4), (2 * w // 3, 3 * h // 4), (45, 50, 60), -1)
        cv2.rectangle(frame, (w // 3, h // 4), (2 * w // 3, 3 * h // 4), (70, 75, 90), 2)

        # Subtle camera sensor noise
        noise = np.random.randint(0, 10, (h, w, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)

        # Automatic periodic motion: every 15 seconds, a 5-second motion event occurs
        cur_sec = int(time.time()) % 15
        motion_active = self._simulated_motion_active or (cur_sec < 5)

        if motion_active:
            # Animate a moving figure / target across the room
            self._anim_x += self._anim_dx
            if self._anim_x > w - 120 or self._anim_x < 80:
                self._anim_dx = -self._anim_dx

            cx = int(self._anim_x)
            cy = int(h // 2 + math.sin(time.time() * 3.0) * 15)

            # Draw moving surveillance object (simulated pedestrian / subject)
            cv2.circle(frame, (cx, cy - 40), 18, (180, 190, 200), -1)  # head
            cv2.ellipse(frame, (cx, cy + 10), (26, 45), 0, 0, 360, (140, 150, 170), -1)  # torso
            cv2.rectangle(frame, (cx - 16, cy + 45), (cx - 4, cy + 90), (100, 110, 130), -1)  # left leg
            cv2.rectangle(frame, (cx + 4, cy + 45), (cx + 16, cy + 90), (100, 110, 130), -1)  # right leg

        return frame

    def _generate_disconnected_frame(self) -> np.ndarray:
        """Render a high-contrast hardware signal lost warning frame."""
        w, h = settings.DEFAULT_FRAME_WIDTH, settings.DEFAULT_FRAME_HEIGHT
        frame = np.full((h, w, 3), (20, 20, 25), dtype=np.uint8)
        cv2.rectangle(frame, (0, 0), (w, 50), (15, 15, 120), -1)
        cv2.rectangle(frame, (0, h - 50), (w, h), (15, 15, 120), -1)
        cv2.putText(frame, "CCTV HARDWARE WARNING", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
        cv2.putText(frame, "PHYSICAL CAMERA SIGNAL LOST", (w // 2 - 180, h // 2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2)
        cv2.putText(frame, "Verify USB cable or camera connection in settings.", (w // 2 - 210, h // 2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        ts_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"TIMESTAMP: {ts_str}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)
        return frame

    def get_standby_jpeg(self) -> bytes:
        """Generate static standby image when monitoring is paused or inactive."""
        w, h = settings.DEFAULT_FRAME_WIDTH, settings.DEFAULT_FRAME_HEIGHT
        frame = np.full((h, w, 3), (15, 23, 42), dtype=np.uint8)
        cv2.rectangle(frame, (20, 20), (w - 20, h - 20), (51, 65, 85), 2)
        cv2.putText(frame, "CCTV INTELLIGENCE SURVEILLANCE", (w // 2 - 220, h // 2 - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (226, 232, 240), 2)
        cv2.putText(frame, "[ STANDBY MODE - MONITORING INACTIVE ]", (w // 2 - 200, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 2)
        cv2.putText(frame, "Click 'Start Live Monitoring' on Dashboard to begin.", (w // 2 - 185, h // 2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (94, 234, 212), 1)
        ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return jpeg.tobytes() if ret else b""

    def _capture_loop(self) -> None:
        """Dedicated thread executing frame acquisition, motion analysis, and sampling."""
        fps_tracker_time = time.monotonic()
        fps_frame_counter = 0
        consecutive_read_failures = 0

        try:
            while not self.stop_event.is_set():
                loop_start = time.monotonic()
                dt = loop_start - self.last_loop_time
                self.last_loop_time = loop_start

                # 1. Acquire raw frame (strictly distinguish physical vs virtual sensor)
                if not self.is_virtual_camera:
                    if self.cap and self.cap.isOpened():
                        ret, frame = self.cap.read()
                        if not ret or frame is None:
                            consecutive_read_failures += 1
                            if consecutive_read_failures >= 10:
                                self.is_connected = False
                                frame = self._generate_disconnected_frame()
                            else:
                                time.sleep(0.03)
                                continue
                        else:
                            consecutive_read_failures = 0
                            self.is_connected = True
                    else:
                        self.is_connected = False
                        frame = self._generate_disconnected_frame()
                else:
                    frame = self._generate_virtual_frame()

                self.total_frames_processed += 1
                fps_frame_counter += 1

                # Update FPS calculation every second
                if loop_start - fps_tracker_time >= 1.0:
                    self.current_fps = round(fps_frame_counter / (loop_start - fps_tracker_time), 1)
                    fps_tracker_time = loop_start
                    fps_frame_counter = 0

                # 2. Motion Detection Pipeline
                activity_state, motion_score, is_motion, fg_mask = self.motion_detector.process_frame(frame)

                # Update duration accumulation
                if activity_state == "ACTIVE":
                    self.active_seconds += dt
                elif activity_state == "DEEP_IDLE":
                    self.deep_idle_seconds += dt
                else:  # IDLE
                    self.idle_seconds += dt

                # 3. Adaptive Frame Sampling
                is_sampled = self.adaptive_sampler.should_sample(activity_state, loop_start)
                if is_sampled:
                    self.total_frames_saved += 1

                # 4. Recording & Event Logging
                if self.recording_manager:
                    self.recording_manager.handle_frame(
                        frame=frame,
                        activity_state=activity_state,
                        motion_score=motion_score,
                        is_sampled=is_sampled,
                    )

                # 5. Annotate Live HUD Frame for MJPEG Stream
                hud_frame = FrameProcessor.add_overlay(
                    frame=frame,
                    camera_name=self.camera_name,
                    activity_state=activity_state,
                    motion_score=motion_score,
                    timestamp=datetime.datetime.now(),
                )

                # 6. Encode JPEG and store in memory buffer
                ret, jpeg = cv2.imencode(
                    ".jpg",
                    hud_frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 75],
                )
                if ret:
                    with self.frame_lock:
                        self.latest_raw_frame = frame
                        self.latest_jpeg_bytes = jpeg.tobytes()

                # Target ~25-30 FPS loop rate
                elapsed = time.monotonic() - loop_start
                sleep_needed = max(0.005, (1.0 / 30.0) - elapsed)
                time.sleep(sleep_needed)
        finally:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            if self.recording_manager:
                try:
                    self.recording_manager.finalize()
                except Exception:
                    pass

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Retrieve the most recent encoded frame for live MJPEG streaming."""
        with self.frame_lock:
            return self.latest_jpeg_bytes

    def get_status(self) -> Dict[str, Any]:
        """Aggregate comprehensive camera, motion, and sampling status."""
        now = time.time()
        uptime = (now - self.start_monitoring_time) if (self.is_monitoring and self.start_monitoring_time) else 0.0

        motion_info = self.motion_detector.get_status()
        sampling_info = self.adaptive_sampler.get_status()

        return {
            "is_connected": self.is_connected,
            "is_monitoring": self.is_monitoring,
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "device_index": self.device_index,
            "is_virtual_camera": self.is_virtual_camera,
            "current_fps": self.current_fps,
            "activity_state": motion_info["activity_state"],
            "sampling_fps": sampling_info["target_fps"],
            "uptime_seconds": round(uptime, 1),
            "total_frames_processed": self.total_frames_processed,
            "total_frames_saved": self.total_frames_saved,
            "motion_score": motion_info["motion_score"],
            "is_motion_detected": motion_info["is_motion_detected"],
            "active_seconds": round(self.active_seconds, 1),
            "idle_seconds": round(self.idle_seconds, 1),
            "deep_idle_seconds": round(self.deep_idle_seconds, 1),
        }


# Global singleton camera manager instance
camera_manager = CameraManager()
