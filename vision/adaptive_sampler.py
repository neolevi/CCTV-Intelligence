"""Adaptive frame sampler based on activity state."""
import time
from typing import Dict, Any, Optional


class AdaptiveSampler:
    """
    Manages dynamic frame sampling frequencies based on current activity state:
    - ACTIVE: e.g. 5.0 FPS
    - IDLE: e.g. 2.0 FPS
    - DEEP_IDLE: e.g. 1.0 FPS
    """

    def __init__(
        self,
        active_fps: float = 5.0,
        idle_fps: float = 2.0,
        deep_idle_fps: float = 1.0,
    ):
        self.active_fps = float(active_fps)
        self.idle_fps = float(idle_fps)
        self.deep_idle_fps = float(deep_idle_fps)

        self.last_sample_time = 0.0
        self.total_frames_evaluated = 0
        self.total_frames_sampled = 0
        self.current_state = "IDLE"

    def update_rates(
        self,
        active_fps: Optional[float] = None,
        idle_fps: Optional[float] = None,
        deep_idle_fps: Optional[float] = None,
    ) -> None:
        """Update target sampling rates dynamically."""
        if active_fps is not None and active_fps > 0:
            self.active_fps = float(active_fps)
        if idle_fps is not None and idle_fps > 0:
            self.idle_fps = float(idle_fps)
        if deep_idle_fps is not None and deep_idle_fps > 0:
            self.deep_idle_fps = float(deep_idle_fps)

    def get_target_fps(self, activity_state: Optional[str] = None) -> float:
        """Get the configured FPS for an activity state."""
        state = (activity_state or self.current_state).upper()
        if state == "ACTIVE":
            return self.active_fps
        elif state == "DEEP_IDLE":
            return self.deep_idle_fps
        else:  # "IDLE"
            return self.idle_fps

    def should_sample(self, activity_state: str, current_time: Optional[float] = None) -> bool:
        """
        Determines whether the incoming frame at current_time should be captured.
        Prevents duplicate captures and guarantees accurate frame intervals.
        """
        now = current_time if current_time is not None else time.monotonic()
        self.current_state = activity_state
        self.total_frames_evaluated += 1

        target_fps = self.get_target_fps(activity_state)
        # Avoid division by zero
        interval = 1.0 / max(0.1, target_fps)

        # First sample or elapsed interval met
        if self.last_sample_time == 0.0 or (now - self.last_sample_time) >= interval:
            self.last_sample_time = now
            self.total_frames_sampled += 1
            return True

        return False

    def reset_stats(self) -> None:
        """Reset frame evaluation counters."""
        self.total_frames_evaluated = 0
        self.total_frames_sampled = 0
        self.last_sample_time = 0.0

    def get_status(self) -> Dict[str, Any]:
        """Return telemetry regarding adaptive sampling."""
        target_fps = self.get_target_fps()
        sampling_ratio = (
            round((self.total_frames_sampled / max(1, self.total_frames_evaluated)) * 100.0, 1)
        )

        return {
            "current_state": self.current_state,
            "target_fps": target_fps,
            "interval_seconds": round(1.0 / max(0.1, target_fps), 3),
            "total_frames_evaluated": self.total_frames_evaluated,
            "total_frames_sampled": self.total_frames_sampled,
            "sampling_efficiency_ratio": sampling_ratio,
        }
