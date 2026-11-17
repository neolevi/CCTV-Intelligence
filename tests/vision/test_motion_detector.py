"""Tests for OpenCV MOG2 Motion Detection Engine."""
import time
import numpy as np
import cv2
import pytest
from vision.motion_detector import MotionDetector


def test_motion_detector_initialization():
    detector = MotionDetector(
        var_threshold=25,
        motion_threshold_percent=1.5,
        idle_timeout=0.2,
        deep_idle_timeout=0.5,
    )
    status = detector.get_status()
    assert status["activity_state"] == "IDLE"
    assert status["motion_score"] == 0.0
    assert status["is_motion_detected"] is False


def test_motion_detection_on_static_frames():
    detector = MotionDetector(
        var_threshold=25,
        motion_threshold_percent=1.5,
        idle_timeout=0.1,
        deep_idle_timeout=0.3,
    )
    static_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Feed several static frames to train background model
    for _ in range(10):
        state, score, is_motion, mask = detector.process_frame(static_frame)

    assert score < 1.0
    assert is_motion is False


def test_motion_detection_on_moving_object():
    detector = MotionDetector(
        var_threshold=16,
        motion_threshold_percent=1.0,
        idle_timeout=0.2,
        deep_idle_timeout=0.5,
    )
    base_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Background training
    for _ in range(15):
        detector.process_frame(base_frame)

    # Injected motion: draw large contrasting rectangle
    motion_frame = base_frame.copy()
    cv2.rectangle(motion_frame, (50, 50), (200, 200), (255, 255, 255), -1)

    state, score, is_motion, mask = detector.process_frame(motion_frame)
    assert score > 1.0
    assert is_motion is True
    assert state == "ACTIVE"


def test_activity_state_transitions():
    detector = MotionDetector(
        var_threshold=16,
        motion_threshold_percent=1.0,
        idle_timeout=0.1,
        deep_idle_timeout=0.3,
    )
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    for _ in range(10):
        detector.process_frame(frame)

    # Motion frame
    m_frame = frame.copy()
    cv2.rectangle(m_frame, (60, 60), (180, 180), (255, 255, 255), -1)
    state, _, is_motion, _ = detector.process_frame(m_frame)
    assert state == "ACTIVE"

    # Wait past idle timeout (0.1s)
    time.sleep(0.15)
    state, _, is_motion, _ = detector.process_frame(frame)
    assert state == "IDLE"

    # Wait past deep idle timeout (0.3s)
    time.sleep(0.35)
    state, _, is_motion, _ = detector.process_frame(frame)
    assert state == "DEEP_IDLE"
