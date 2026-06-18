"""
AutoApply — FastAPI Main Application

Entry point for the backend server.
Mounts all API routes, WebSocket notifications, and CORS middleware.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api.profile import router as profile_router
from app.api.preferences import router as preferences_router
from app.api.jobs import router as jobs_router
from app.api.applications import router as applications_router
from app.api.chatbot import router as chatbot_router
from app.services.notification import register_client, unregister_client, send_notification

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup
    logger.info("🚀 employment starting up...")
    await init_db()
    logger.info("✅ Database initialized")

    # Ensure directories exist
    settings.upload_path
    settings.generated_path
    logger.info("✅ Storage directories ready")

    yield

    # Shutdown
    logger.info("👋 employment shutting down...")


# Create FastAPI app
app = FastAPI(
    title="employment",
    description="Autonomous Job Application Agent — API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)

async def verify_api_token(api_token: str = Security(api_key_header)):
    if settings.api_token and api_token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Token header",
        )

# Mount API routes
app.include_router(profile_router, dependencies=[Depends(verify_api_token)] if settings.api_token else [])
app.include_router(preferences_router, dependencies=[Depends(verify_api_token)] if settings.api_token else [])
app.include_router(jobs_router, dependencies=[Depends(verify_api_token)] if settings.api_token else [])
app.include_router(applications_router, dependencies=[Depends(verify_api_token)] if settings.api_token else [])
app.include_router(chatbot_router, dependencies=[Depends(verify_api_token)] if settings.api_token else [])

# Static files for generated resumes/cover letters
try:
    app.mount(
        "/generated",
        StaticFiles(directory=str(settings.generated_path)),
        name="generated",
    )
except Exception:
    logger.warning("Generated files directory not ready yet")


# ── WebSocket for real-time notifications ─────────────────────
@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str | None = None):
    """
    WebSocket endpoint for real-time desktop notifications.
    The frontend connects here and uses the Browser Notification API
    to show native desktop popups.
    """
    if settings.api_token and token != settings.api_token:
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await register_client(websocket)

    try:
        while True:
            # Keep connection alive, receive heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await unregister_client(websocket)


# ── Health Check ──────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
    }


# ── Dashboard Stats ──────────────────────────────────────────
@app.get("/api/dashboard", dependencies=[Depends(verify_api_token)] if settings.api_token else [])
async def dashboard_stats():
    """Quick stats for the dashboard."""
    from sqlalchemy import select, func
    from app.core.database import async_session_factory
    from app.models.job import Job
    from app.models.application import Application

    async with async_session_factory() as session:
        # Job counts by status
        job_counts = await session.execute(
            select(Job.status, func.count(Job.id)).group_by(Job.status)
        )
        jobs_by_status = dict(job_counts.all())

        # Total jobs
        total_jobs = sum(jobs_by_status.values())

        # High match jobs (score >= 70)
        high_match = await session.execute(
            select(func.count(Job.id)).where(Job.match_score >= 70)
        )
        high_match_count = high_match.scalar() or 0

        # Application counts
        app_counts = await session.execute(
            select(Application.status, func.count(Application.id))
            .group_by(Application.status)
        )
        apps_by_status = dict(app_counts.all())

        # Recent jobs (last 10)
        recent = await session.execute(
            select(Job)
            .order_by(Job.discovered_at.desc())
            .limit(10)
        )
        recent_jobs = recent.scalars().all()

    return {
        "total_jobs_discovered": total_jobs,
        "high_match_jobs": high_match_count,
        "jobs_by_status": jobs_by_status,
        "applications_by_status": apps_by_status,
        "recent_jobs": [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "match_score": j.match_score,
                "status": j.status,
                "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
            }
            for j in recent_jobs
        ],
    }


# ── Broadcast Endpoint for Inter-Process Notifications ──────────
@app.post("/api/notifications/broadcast", dependencies=[Depends(verify_api_token)] if settings.api_token else [])
async def broadcast_notification(payload: dict):
    """Broadcast notification from other containers (Celery) to browser clients."""
    await send_notification(
        title=payload.get("title", ""),
        body=payload.get("body", ""),
        notification_type=payload.get("notification_type", "info"),
        data=payload.get("data", {}),
        local_only=True,
    )
    return {"status": "broadcasted"}

