"""Motion detection engine using OpenCV MOG2 background subtraction."""
import time
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np


class MotionDetector:
    """
    OpenCV-based motion detector using MOG2 background subtractor.
    Classifies camera activity into ACTIVE, IDLE, and DEEP_IDLE.
    """

    def __init__(
        self,
        var_threshold: int = 25,
        detect_shadows: bool = True,
        motion_threshold_percent: float = 1.5,
        idle_timeout: float = 5.0,
        deep_idle_timeout: float = 20.0,
        processing_width: int = 320,
        processing_height: int = 240,
    ):
        self.var_threshold = var_threshold
        self.detect_shadows = detect_shadows
        self.motion_threshold_percent = motion_threshold_percent
        self.idle_timeout = idle_timeout
        self.deep_idle_timeout = deep_idle_timeout
        self.processing_width = processing_width
        self.processing_height = processing_height

        # Initialize MOG2 Subtractor
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows,
        )

        # Internal state tracking
        self.current_state = "IDLE"  # "ACTIVE", "IDLE", "DEEP_IDLE"
        self.last_motion_time = time.time()
        self.state_enter_time = time.time()
        self.last_motion_score = 0.0
        self.is_motion_detected = False

    def update_settings(
        self,
        sensitivity: Optional[int] = None,
        motion_threshold_percent: Optional[float] = None,
        idle_timeout: Optional[float] = None,
        deep_idle_timeout: Optional[float] = None,
    ) -> None:
        """Update detection settings dynamically."""
        if sensitivity is not None and sensitivity != self.var_threshold:
            self.var_threshold = sensitivity
            self.subtractor.setVarThreshold(self.var_threshold)

        if motion_threshold_percent is not None:
            self.motion_threshold_percent = motion_threshold_percent

        if idle_timeout is not None:
            self.idle_timeout = idle_timeout

        if deep_idle_timeout is not None:
            self.deep_idle_timeout = deep_idle_timeout

    def process_frame(self, frame: np.ndarray) -> Tuple[str, float, bool, np.ndarray]:
        """
        Processes a raw frame through the motion pipeline:
        1. Resize for efficient computation
        2. Apply MOG2 background subtraction
        3. Threshold shadows
        4. Noise reduction using median blur / morphological operations
        5. Calculate motion score (% of frame pixels in motion)
        6. Determine activity state with hysteresis

        Returns:
            (activity_state, motion_score, is_motion_detected, fg_mask)
        """
        now = time.time()
        h, w = frame.shape[:2]

        # 1. Resize for fast processing if larger than processing target
        if w > self.processing_width or h > self.processing_height:
            resized = cv2.resize(
                frame,
                (self.processing_width, self.processing_height),
                interpolation=cv2.INTER_LINEAR,
            )
        else:
            resized = frame

        # 2. Apply MOG2 background subtractor
        fg_mask = self.subtractor.apply(resized)

        # 3. Threshold to remove shadows (MOG2 marks shadows as 127)
        # We only keep definite foreground (250-255)
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # 4. Noise reduction using median blur
        thresh = cv2.medianBlur(thresh, 5)

        # Dilate slightly to connect fragmented movement blobs
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # 5. Calculate motion pixels and percentage
        total_pixels = thresh.shape[0] * thresh.shape[1]
        motion_pixels = cv2.countNonZero(thresh)
        motion_score = (motion_pixels / total_pixels) * 100.0
        self.last_motion_score = round(motion_score, 2)

        # 6. Evaluate motion threshold
        self.is_motion_detected = motion_score >= self.motion_threshold_percent

        prev_state = self.current_state

        if self.is_motion_detected:
            self.last_motion_time = now
            self.current_state = "ACTIVE"
        else:
            time_since_motion = now - self.last_motion_time
            if time_since_motion < self.idle_timeout:
                self.current_state = "ACTIVE"  # Keep active during short pause in motion
            elif time_since_motion < self.deep_idle_timeout:
                self.current_state = "IDLE"
            else:
                self.current_state = "DEEP_IDLE"

        if self.current_state != prev_state:
            self.state_enter_time = now

        return self.current_state, self.last_motion_score, self.is_motion_detected, thresh

    def get_status(self) -> Dict[str, Any]:
        """Return the current motion detection telemetry."""
        now = time.time()
        time_since_motion = now - self.last_motion_time
        remaining_active = max(0.0, self.idle_timeout - time_since_motion)

        return {
            "activity_state": self.current_state,
            "motion_score": self.last_motion_score,
            "is_motion_detected": self.is_motion_detected,
            "time_in_current_state": round(now - self.state_enter_time, 2),
            "active_timeout_remaining": round(remaining_active, 2),
        }
