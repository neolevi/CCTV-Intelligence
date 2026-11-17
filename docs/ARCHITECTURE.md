# CCTV Intelligence — Architectural Specification

## 1. System Philosophy
Traditional CCTV surveillance systems write constant bitrate video streams 24/7, resulting in massive storage overhead and arduous video review workflows. **CCTV Intelligence** addresses this through:
1. **Activity-Driven Sampling:** Adjusting capture frequency based on detected scene activity.
2. **Automated Daily Surveillance Intelligence:** Synthesizing millions of potential frames into concise, queryable, deterministic surveillance summaries with natural language narratives.

---

## 2. Layered Architecture

### A. Vision Layer (`vision/`)
- **`CameraManager`:** Threaded controller managing camera device enumeration (DirectShow/V4L2), frame acquisition, live HUD annotation, MJPEG streaming buffers, and session tracking.
- **`MotionDetector`:** High-performance background subtractor based on OpenCV's MOG2 (`cv2.createBackgroundSubtractorMOG2`). Employs shadow thresholding (filtering gray pixels with value 127) and median blur morphology to isolate valid foreground motion. Computes the percentage of moving pixels against configurable thresholds.
- **`AdaptiveSampler`:** Enforces precise frame interval timing according to the current activity classification:
  - `ACTIVE`: default 5.0 FPS (0.2s interval)
  - `IDLE`: default 2.0 FPS (0.5s interval)
  - `DEEP_IDLE`: default 1.0 FPS (1.0s interval)
- **`RecordingManager`:** Handles `cv2.VideoWriter` lifecycle for `.mp4` video clips, writes individual evidence keyframes to `storage/frames/{date}/`, generates event thumbnails, and commits relational records to SQLite.
- **`FrameProcessor`:** Annotates surveillance frames with live timecode, camera name, and state badges.

---

### B. Storage & Database Layer (`backend/database.py`, `backend/models.py`)
Relational SQLite schema managed with SQLAlchemy:
- `users`: Operator credentials, Argon2 password hashes, and roles.
- `cameras`: Camera definitions, resolution, hardware device index, and connection status.
- `monitoring_sessions`: Continuous surveillance sessions with active/idle duration totals.
- `motion_events`: Verified movement incidents with start/end timestamps and peak motion scores.
- `captured_frames`: Individual keyframes saved by the adaptive sampler.
- `recordings`: Continuous video clips generated during ACTIVE activity states.
- `daily_summaries`: Aggregated daily metrics, peak activity windows, and synthesized natural-language summaries.
- `settings`: Key-value configuration parameters persisted across application restarts.

---

### C. Application & API Layer (`backend/main.py`)
- **FastAPI Core:** ASGI application exposing REST endpoints and WebSocket telemetry.
- **Authentication:** JWT Bearer tokens with Argon2 password hashing.
- **MJPEG Streaming:** Multipart HTTP response (`multipart/x-mixed-replace; boundary=frame`) for low-latency live preview.
- **Static Asset Serving:** Mounted `/storage` endpoint for thumbnails and media access.

---

### D. Presentation Layer (`frontend/`)
- **React 19 + TypeScript + Vite:** Fast, modern single-page surveillance dashboard.
- **Overview Dashboard:** Highlights the live camera preview alongside the Daily Intelligence Summary.
- **24-Hour Interactive Timeline:** Half-hour interval state blocks displaying ACTIVE, IDLE, DEEP IDLE, and OFFLINE windows.
- **Activity & Trend Analytics:** SVG-based responsive bar and trend charts.
- **Modals:** Video playback for generated MP4 clips and keyframe inspection galleries.
