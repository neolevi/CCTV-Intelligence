"""Tests for Camera Manager and lifecycle."""
import time
import pytest
from vision.camera_manager import CameraManager


def test_list_devices():
    cam_mgr = CameraManager()
    devices = cam_mgr.list_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0
    # Must have the virtual camera option for automated environments
    virtual_devs = [d for d in devices if d["index"] == -1]
    assert len(virtual_devs) == 1


def test_camera_monitoring_lifecycle():
    cam_mgr = CameraManager()
    if cam_mgr.is_monitoring:
        cam_mgr.stop_monitoring()

    # Start monitoring in simulated mode
    success = cam_mgr.start_monitoring(camera_id=1, device_index=-1)
    assert success is True
    assert cam_mgr.is_monitoring is True

    # Allow a few frames to process and wait for initial frame encode
    jpeg_bytes = None
    for _ in range(40):
        jpeg_bytes = cam_mgr.get_latest_jpeg()
        if jpeg_bytes is not None and cam_mgr.total_frames_processed > 0:
            break
        time.sleep(0.05)

    status = cam_mgr.get_status()
    assert status["is_monitoring"] is True
    assert status["total_frames_processed"] > 0

    # Verify JPEG frame generation
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 100
    # JPEG header magic bytes
    assert jpeg_bytes[:2] == b"\xff\xd8"

    # Stop monitoring
    stop_success = cam_mgr.stop_monitoring()
    assert stop_success is True
    assert cam_mgr.is_monitoring is False
