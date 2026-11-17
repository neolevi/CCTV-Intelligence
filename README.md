# CCTV Intelligence
> **Motion-Adaptive CCTV Surveillance with Automated Daily Summarization**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9+-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 1. System Overview

**CCTV Intelligence** is an autonomous, full-stack surveillance web application engineered to solve storage bloat and review fatigue in standard continuous video recording systems.

By coupling an **OpenCV MOG2 background subtractor** with a **dynamic adaptive frame sampler**, the system intelligently scales capture rates based on scene activity:
- **ACTIVE (5.0 FPS):** Initiates automatic video recording clips (`.mp4`), logs high-frequency keyframes, and flags verified motion events.
- **IDLE (2.0 FPS):** Maintains baseline situational awareness during static conditions.
- **DEEP IDLE (1.0 FPS):** Conserves up to 90% storage during extended dormant hours.

A major core feature of CCTV Intelligence is its **Automated Daily Surveillance Summary engine**, displayed prominently directly on the main dashboard. It computes deterministic activity analytics, renders an interactive 24-hour timeline, tracks storage consumption, and synthesizes human-readable natural language daily surveillance narratives.

---

## 2. Architecture & Pipeline

```text
┌─────────────────┐       Raw Frame Capture (30 FPS)
│  Physical Webcam│ ────────────────────────────────────┐
│   or Simulated  │                                     │
│  Surveillance   │                                     ▼
└─────────────────┘                       ┌───────────────────────────┐
                                          │ OpenCV Motion Detector    │
                                          │ - MOG2 Subtraction        │
                                          │ - Shadow Thresholding     │
                                          │ - Median Blur / Dilation  │
                                          │ - % Motion Pixel Score    │
                                          └─────────────┬─────────────┘
                                                        │ Activity State
                                                        ▼ (ACTIVE / IDLE / DEEP_IDLE)
┌─────────────────────────────────┐       ┌───────────────────────────┐
│     Live Surveillance Feed      │ ◄──── │  Adaptive Frame Sampler   │
│ - MJPEG Stream (/api/camera/...)│       │ - ACTIVE:    5.0 FPS      │
│ - Live HUD Telemetry & State    │       │ - IDLE:      2.0 FPS      │
└─────────────────────────────────┘       │ - DEEP IDLE: 1.0 FPS      │
                                          └─────────────┬─────────────┘
                                                        │ Sampled Frames
                                                        ▼
                                          ┌───────────────────────────┐
                                          │   Recording & Event Mgr   │
                                          │ - MotionEvent Logging     │
                                          │ - MP4 Video Writer Clips  │
                                          │ - Keyframe Persistence    │
                                          │ - JPEG Thumbnails         │
                                          └─────────────┬─────────────┘
                                                        │
                         ┌──────────────────────────────┴──────────────────────────────┐
                         ▼                                                             ▼
┌─────────────────────────────────────────────────┐   ┌─────────────────────────────────────────────────┐
│              SQLite Database                    │   │              Physical Storage                   │
│ - users, cameras, monitoring_sessions           │   │ - storage/recordings/{date}/rec_*.mp4           │
│ - motion_events, captured_frames, recordings    │   │ - storage/frames/{date}/frame_*.jpg             │
│ - daily_summaries, settings                     │   │ - storage/thumbnails/{date}/thumb_*.jpg         │
└────────────────────────┬────────────────────────┘   └─────────────────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                     Automated Daily Intelligence Engine                               │
│ - 24-Hour Activity Timeline Segments & Granular State Tracking                        │
│ - Deterministic Hourly Motion Distribution                                            │
│ - Natural-Language Daily Surveillance Narrative Synthesis                             │
│ - Markdown Daily Surveillance Report Export                                           │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Features

- **Real Camera Hardware & Simulated Fallback:** Automatic detection of USB webcams with a built-in virtual surveillance sensor fallback, allowing testing and operation on machines without physical webcams.
- **OpenCV MOG2 Motion Engine:** Background subtraction with shadow suppression, noise reduction morphology, and configurable sensitivity thresholds.
- **Adaptive Frame Sampling:** Hysteresis-driven state switching across ACTIVE (5 FPS), IDLE (2 FPS), and DEEP IDLE (1 FPS).
- **Video Recording Clips & Keyframes:** Genuine `.mp4` video files generated via `cv2.VideoWriter`, timestamped keyframes, and instant event thumbnail generation.
- **Prominent Daily Summary on Main Dashboard:** Never buried in submenus; displays today's surveillance narrative, key metrics, timeline, and report export on the home screen.
- **Interactive 24-Hour Timeline:** Hoverable/clickable half-hour blocks depicting state distributions and event counts.
- **Historical Analytics:** Multi-day motion trends, hourly distributions, active vs. idle ratio charts, and storage telemetry.
- **Full Operator Security:** Argon2 password hashing, JWT bearer tokens, protected routes, and session restore.
- **Dark & Light Mode:** Sleek surveillance tech aesthetic with accessible contrast and instant toggle.

---

## 4. Technology Stack

### Backend
- **Python 3.13 / 3.15**
- **FastAPI:** High-performance REST API and WebSocket streaming
- **Uvicorn:** ASGI web server
- **SQLAlchemy:** Relational ORM with connection pooling
- **SQLite3:** Embedded relational storage with foreign keys and indexes
- **OpenCV (cv2):** Computer vision, MOG2 background subtractor, and VideoWriter
- **NumPy:** Vectorized frame processing
- **Argon2 & PyJWT:** Cryptographic password hashing and JWT token issuance

### Frontend
- **React 19**
- **TypeScript**
- **Vite:** Next-generation frontend build tooling
- **Lucide Icons:** Clean surveillance iconography
- **Custom SVG Charting:** Zero-dependency, responsive 24-hour timelines and distribution graphs

---

## 5. Quick Start (Windows & Cross-Platform)

### Prerequisites
1. **Python 3.10+** (tested through 3.15)
2. **Node.js 18+** & **npm**

### Step 1: Clone or Navigate to Directory
```powershell
cd CCTV-Intelligence
```

### Step 2: Set Up Python Virtual Environment
```powershell
# Create dedicated virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# (or in cmd.exe: .venv\Scripts\activate.bat)

# Install backend dependencies
pip install -r requirements.txt
```

### Step 3: Set Up Frontend
```powershell
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Run the Application
You can launch both the FastAPI backend and React frontend concurrently with a single command:
```powershell
python start.py
```

Or run individual services:
```powershell
# Run only FastAPI backend (http://127.0.0.1:8000)
python start.py --backend

# Run only Vite frontend (http://localhost:5173)
python start.py --frontend

# Initialize / re-seed database
python start.py --init-db

# Run automated test suite
python start.py --test
```

---

## 6. Default Credentials

The database is seeded with a default surveillance administrator account:
- **Email:** `admin@cctv.local`
- **Password:** `AdminPass123!`

New user registration is also available directly on the sign-in page.

---

## 7. Interactive Testing with Virtual Camera

If your computer does not have a physical webcam attached, CCTV Intelligence automatically falls back to its **Simulated Surveillance Sensor**:
1. Log in with the default admin credentials.
2. In the **Live Surveillance Feed** card on the Overview dashboard, select **"Simulated CCTV Feed (Virtual Sensor)"**.
3. Click **"Start Monitoring"** to activate live streaming.
4. Click **"Inject Motion Event"** to simulate moving pedestrian targets:
   - Observe the live **Activity State** switch from `IDLE` to `ACTIVE`.
   - Observe the **Sampling Rate** dynamically jump to `5.0 FPS`.
   - Watch the **Motion Events** counter increment.
   - Review the newly recorded `.mp4` video clip in the **Recent Video Clips** row or on the **Recordings** page.
   - Click **"Report"** on the Daily Summary to export the generated Markdown surveillance report!

---

## 8. REST API Documentation

FastAPI provides interactive Swagger UI documentation at:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate and receive JWT token |
| `POST` | `/api/auth/register` | Register new surveillance operator |
| `GET` | `/api/auth/me` | Current authenticated operator info |
| `GET` | `/api/camera/devices` | Enumerate connected webcams & virtual sensor |
| `GET` | `/api/camera/status` | Live camera telemetry, FPS, and activity state |
| `POST` | `/api/camera/start` | Start live surveillance monitoring |
| `POST` | `/api/camera/stop` | Stop monitoring and release camera resources |
| `GET` | `/api/camera/stream` | Multipart/x-mixed-replace live MJPEG video stream |
| `POST` | `/api/camera/trigger_motion` | Inject/reset test motion target |
| `GET` | `/api/motion/status` | Current motion score and state timeouts |
| `GET` | `/api/motion/statistics` | Today's active/idle duration breakdown |
| `GET` | `/api/frames` | List captured keyframes with pagination and state filter |
| `GET` | `/api/frames/{id}/image` | Serve raw JPEG keyframe |
| `GET` | `/api/events` | List detected motion events with date filter |
| `GET` | `/api/events/{id}` | Event details with correlated keyframe gallery |
| `GET` | `/api/recordings` | List video clips with duration and file sizes |
| `GET` | `/api/recordings/{id}/stream`| Stream recorded MP4 video for HTML5 playback |
| `GET` | `/api/recordings/{id}/download`| Download raw video clip |
| `GET` | `/api/summaries/daily` | Today's surveillance summary & narrative |
| `GET` | `/api/summaries/daily/{date}` | Historical summary for date (YYYY-MM-DD) |
| `POST` | `/api/summaries/generate/{date}` | On-demand recalculation of daily summary |
| `GET` | `/api/summaries/{date}/download` | Download comprehensive Markdown summary report |
| `GET` | `/api/analytics/overview` | Overall surveillance KPIs |
| `GET` | `/api/analytics/trends` | Historical motion & storage trends (7-30 days) |
| `GET` | `/api/settings` | Retrieve active system parameters and disk usage |
| `PUT` | `/api/settings` | Update sensitivity, thresholds, and FPS rates |

---

## 9. Automated Testing

The automated test suite covers the entire surveillance pipeline without requiring external camera hardware:
```powershell
# Run all tests via start.py
python start.py --test

# Or run pytest directly
.\.venv\Scripts\pytest -v tests
```

### Test Coverage Highlights
- **Vision Pipeline (`tests/vision/`):** Motion detector initialization, static scene suppression, motion detection on moving objects, state hysteresis, adaptive sampler FPS calculations, camera manager lifecycle, and recording manager video writing.
- **Backend Services (`tests/backend/`):** Password hashing, JWT token lifecycle, login, registration, duplicate prevention, settings mutation, analytics aggregation, and daily summary generation.
- **Integration (`tests/integration/`):** Full end-to-end loop: camera start → simulated motion injection → MOG2 detection → adaptive sampling → database event creation → video file finalization → daily summary synthesis.

---

## 10. License
This project is licensed under the MIT License.
