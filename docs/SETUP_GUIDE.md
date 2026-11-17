# CCTV Intelligence — Setup & Installation Guide

This guide covers complete local installation and setup on **Windows 10/11** and cross-platform environments.

---

## 1. Prerequisites

Ensure the following tools are installed:
- **Python 3.10+** (Python 3.12, 3.13, 3.15 supported)
  - Verify: `python --version`
- **Node.js 18+** & **npm**
  - Verify: `node --version` and `npm --version`
- **Git**

---

## 2. Directory Layout & Isolation

All files reside inside the dedicated `CCTV-Intelligence` directory:

```text
CCTV-Intelligence/
├── backend/          # FastAPI REST endpoints, auth, and database models
├── frontend/         # React + TypeScript + Vite SPA
├── vision/           # OpenCV MOG2 motion detector & adaptive sampler
├── storage/          # Local media storage (recordings, keyframes, thumbnails)
├── tests/            # Automated pytest test suite
├── docs/             # Technical specifications & guides
├── .env.example      # Environment variable template
├── requirements.txt  # Python package dependencies
├── start.py          # Unified application runner
└── README.md
```

---

## 3. Step-by-Step Installation

### Step 3.1: Python Virtual Environment
Open PowerShell inside `CCTV-Intelligence`:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# If PowerShell execution policy blocks activation, run in standard cmd.exe:
# .venv\Scripts\activate.bat

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.2: Environment Configuration
Copy the provided `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

The default values are pre-configured for local surveillance operation with SQLite.

### Step 3.3: Frontend Dependencies
```powershell
cd frontend
npm install
npm run build
cd ..
```

---

## 4. Initializing the Database

Initialize the SQLite database schema and seed the default operator account:

```powershell
python start.py --init-db
```

Default credentials created:
- **Email:** `admin@cctv.local`
- **Password:** `AdminPass123!`

---

## 5. Starting the Application

Launch both the backend and frontend simultaneously:

```powershell
python start.py
```

- **Surveillance UI:** [http://localhost:5173](http://localhost:5173)
- **API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 6. Running Automated Tests

Run the full automated test suite (vision pipeline, backend APIs, integration):

```powershell
python start.py --test
```

All 26 tests will execute using synthetic surveillance sensors without requiring a physical webcam.
