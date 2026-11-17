"""Frame processing, overlay annotation, thumbnail generation, and storage utilities."""
import datetime
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class FrameProcessor:
    """Utilities for processing, annotating, resizing, and saving frames."""

    @staticmethod
    def add_overlay(
        frame: np.ndarray,
        camera_name: str,
        activity_state: str,
        motion_score: float,
        timestamp: Optional[datetime.datetime] = None,
    ) -> np.ndarray:
        """Draw an informational HUD overlay onto the surveillance frame."""
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        dt = timestamp or datetime.datetime.now()
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        # Color based on activity state (BGR)
        if activity_state == "ACTIVE":
            badge_color = (0, 0, 230)  # Red
        elif activity_state == "IDLE":
            badge_color = (0, 200, 255)  # Amber
        else:  # DEEP_IDLE
            badge_color = (0, 200, 0)  # Green

        # Top banner background (semi-transparent)
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, 36), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

        # Left label: Camera Name & State Badge
        cv2.circle(annotated, (16, 18), 7, badge_color, -1)
        text_cam = f"{camera_name} | {activity_state} ({motion_score:.1f}%)"
        cv2.putText(
            annotated,
            text_cam,
            (32, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (240, 240, 240),
            1,
            cv2.LINE_AA,
        )

        # Right label: Timestamp
        (tw, th), _ = cv2.getTextSize(timestamp_str, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.putText(
            annotated,
            timestamp_str,
            (w - tw - 12, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )

        return annotated

    @staticmethod
    def generate_thumbnail(
        frame: np.ndarray,
        output_path: Path,
        size: Tuple[int, int] = (320, 240),
    ) -> str:
        """Create and save a thumbnail for an event or recording."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumb = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(output_path), thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return str(output_path)

    @staticmethod
    def save_frame(
        frame: np.ndarray,
        output_path: Path,
        quality: int = 85,
    ) -> str:
        """Save a frame to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return str(output_path)
