"""Vision package for CCTV Intelligence."""
from vision.motion_detector import MotionDetector
from vision.adaptive_sampler import AdaptiveSampler
from vision.frame_processor import FrameProcessor
from vision.recording_manager import RecordingManager
from vision.camera_manager import CameraManager, camera_manager

__all__ = [
    "MotionDetector",
    "AdaptiveSampler",
    "FrameProcessor",
    "RecordingManager",
    "CameraManager",
    "camera_manager",
]
