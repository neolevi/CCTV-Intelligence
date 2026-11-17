#!/usr/bin/env python3
"""
CCTV Intelligence — Application Launch & Orchestration Script.
Starts backend FastAPI service and frontend Vite development server concurrently.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Locate Python in .venv if available
if os.name == "nt":
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    NPM_CMD = "npm.cmd"
else:
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
    NPM_CMD = "npm"

PYTHON_BIN = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def init_database():
    """Initialize SQLite database and populate default admin."""
    print("=" * 60)
    print("  Initializing CCTV Intelligence Database...")
    print("=" * 60)
    res = subprocess.run([PYTHON_BIN, str(PROJECT_ROOT / "backend" / "init_db_cli.py")])
    if res.returncode == 0:
        print("[SUCCESS] Database initialization completed.")
    else:
        print("[ERROR] Database initialization failed.")
    return res.returncode


def run_tests():
    """Run full automated pytest test suite."""
    print("=" * 60)
    print("  Running CCTV Intelligence Automated Test Suite...")
    print("=" * 60)
    pytest_bin = str(PROJECT_ROOT / ".venv" / "Scripts" / "pytest.exe") if os.name == "nt" else "pytest"
    res = subprocess.run([pytest_bin, "-v", "tests"], cwd=str(PROJECT_ROOT))
    return res.returncode


def wait_for_backend_health(url: str = "http://127.0.0.1:8000/api/health", timeout_sec: float = 15.0) -> bool:
    """Poll the backend health check endpoint until active or timeout."""
    start_t = time.time()
    print("[BACKEND] Waiting for backend service readiness check...")
    while time.time() - start_t < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CCTV-Intelligence-Startup"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "healthy":
                        print(f"[READY] Backend responded healthy in {time.time() - start_t:.1f}s.")
                        return True
        except Exception:
            time.sleep(0.4)
    print(f"[WARNING] Backend did not respond within {timeout_sec}s.")
    return False


def start_backend():
    """Launch FastAPI backend server on port 8000."""
    print("[BACKEND] Launching FastAPI server on http://127.0.0.1:8000 ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.Popen(
        [
            PYTHON_BIN,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
    )


def start_frontend():
    """Launch Vite frontend server on port 5173."""
    print("[FRONTEND] Launching Vite frontend on http://localhost:5173 ...")
    frontend_dir = PROJECT_ROOT / "frontend"
    return subprocess.Popen(
        [NPM_CMD, "run", "dev"],
        cwd=str(frontend_dir),
    )


def main():
    parser = argparse.ArgumentParser(description="CCTV Intelligence Launcher")
    parser.add_argument("--backend", action="store_true", help="Launch only FastAPI backend")
    parser.add_argument("--frontend", action="store_true", help="Launch only Vite frontend")
    parser.add_argument("--init-db", action="store_true", help="Initialize database and exit")
    parser.add_argument("--test", action="store_true", help="Run automated test suite and exit")
    args = parser.parse_args()

    if args.init_db:
        sys.exit(init_database())

    if args.test:
        sys.exit(run_tests())

    # Ensure DB is initialized; abort if initialization fails
    db_rc = init_database()
    if db_rc != 0:
        print("[CRITICAL] Database initialization failed. Aborting application startup.")
        sys.exit(db_rc)

    processes = []

    print("\n" + "=" * 60)
    print("   CCTV INTELLIGENCE — SURVEILLANCE & DAILY SUMMARIZATION")
    print("=" * 60)
    print(" System operator initialized. Configuration loaded securely from .env.")
    print("=" * 60 + "\n")

    try:
        if args.backend:
            proc = start_backend()
            processes.append(proc)
            wait_for_backend_health()
            proc.wait()
        elif args.frontend:
            proc = start_frontend()
            processes.append(proc)
            proc.wait()
        else:
            # Concurrently launch both services with proper health readiness polling
            b_proc = start_backend()
            processes.append(b_proc)

            is_ready = wait_for_backend_health()
            if not is_ready and b_proc.poll() is not None:
                print("[CRITICAL] Backend process terminated unexpectedly during startup.")
                sys.exit(1)

            f_proc = start_frontend()
            processes.append(f_proc)

            print("\n[ACTIVE] CCTV Intelligence is running.")
            print("  Frontend UI: http://localhost:5173")
            print("  API Docs:    http://127.0.0.1:8000/docs")
            print("Press Ctrl+C to terminate both servers.\n")

            while True:
                time.sleep(1)
                # If either process died, exit
                if b_proc.poll() is not None or f_proc.poll() is not None:
                    break

    except KeyboardInterrupt:
        print("\nShutting down CCTV Intelligence services...")
    finally:
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                p.kill()
        print("All processes terminated cleanly.")


if __name__ == "__main__":
    main()
