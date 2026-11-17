"""Main FastAPI application entry point for CCTV Intelligence."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.auth.routes import router as auth_router
from backend.cameras.routes import router as camera_router
from backend.motion.routes import router as motion_router
from backend.frames.routes import router as frames_router
from backend.events.routes import router as events_router
from backend.recordings.routes import router as recordings_router
from backend.summaries.routes import router as summaries_router
from backend.analytics.routes import router as analytics_router
from backend.settings.routes import router as settings_router
from vision.camera_manager import camera_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize database and handle cleanup on shutdown."""
    # Startup
    init_db()
    yield
    # Shutdown
    camera_manager.stop_monitoring()


app = FastAPI(
    title="CCTV Intelligence API",
    description="Motion-Adaptive CCTV Recording with Automated Daily Surveillance Summarization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for storage (recordings, thumbnails, frames)
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Include Modular Routers
app.include_router(auth_router)
app.include_router(camera_router)
app.include_router(motion_router)
app.include_router(frames_router)
app.include_router(events_router)
app.include_router(recordings_router)
app.include_router(summaries_router)
app.include_router(analytics_router)
app.include_router(settings_router)


@app.get("/api/health")
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "camera_monitoring": camera_manager.is_monitoring,
    }


@app.websocket("/api/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Real-time WebSocket feed pushing camera & motion telemetry to frontend clients."""
    await websocket.accept()
    try:
        while True:
            status = camera_manager.get_status()
            await websocket.send_json(status)
            await asyncio.sleep(0.5)  # 2 Hz telemetry update
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
