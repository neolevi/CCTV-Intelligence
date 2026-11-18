"""Pytest configuration and test database fixtures."""
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db
from vision.camera_manager import camera_manager


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure all tables and default records exist before running tests."""
    init_db()


@pytest.fixture(autouse=True)
def isolate_camera_manager_state():
    """Ensure camera_manager is stopped before and after each test for strict isolation."""
    if camera_manager.is_monitoring:
        camera_manager.stop_monitoring()
    yield
    if camera_manager.is_monitoring:
        camera_manager.stop_monitoring()
