"""
AutoApply — Notification Service

Sends desktop notifications via the Browser Notification API (WebSocket push).
The frontend subscribes to a WebSocket and displays native desktop notifications.
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# In-memory list of connected WebSocket clients
# (In production, use Redis pub/sub for multi-process support)
connected_clients: list[Any] = []


async def register_client(websocket):
    """Register a WebSocket client for notifications."""
    connected_clients.append(websocket)
    logger.info(f"Notification client connected. Total: {len(connected_clients)}")


async def unregister_client(websocket):
    """Remove a disconnected WebSocket client."""
    if websocket in connected_clients:
        connected_clients.remove(websocket)
    logger.info(f"Notification client disconnected. Total: {len(connected_clients)}")


async def send_notification(
    title: str,
    body: str,
    notification_type: str = "info",
    data: dict | None = None,
    local_only: bool = False,
):
    """
    Send a notification to all connected WebSocket clients.
    If we are in the worker process (no connected clients), forward to web server.
    """
    import httpx
    
    message = {
        "type": "notification",
        "notification_type": notification_type,  # info, success, warning, job_match
        "title": title,
        "body": body,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    if connected_clients:
        payload = json.dumps(message)
        disconnected = []

        for client in connected_clients:
            try:
                await client.send_text(payload)
            except Exception:
                disconnected.append(client)

        # Clean up disconnected clients
        for client in disconnected:
            await unregister_client(client)

        logger.info(
            f"Notification sent to {len(connected_clients) - len(disconnected)} clients: {title}"
        )
    elif not local_only:
        # Forward via HTTP to web container so it can broadcast to its in-memory WebSocket clients
        try:
            headers = {}
            from app.core.config import settings
            if settings.api_token:
                headers["X-API-Token"] = settings.api_token

            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://web:8000/api/notifications/broadcast",
                    json={
                        "title": title,
                        "body": body,
                        "notification_type": notification_type,
                        "data": data or {},
                    },
                    headers=headers,
                    timeout=2.0
                )
            logger.info(f"Forwarded notification to web container: {title}")
        except Exception as e:
            logger.warning(f"Could not forward notification to web container: {e}")



async def notify_new_job_match(
    job_title: str,
    company: str,
    match_score: float,
    job_id: int,
):
    """Send a notification for a new high-match job discovery."""
    await send_notification(
        title=f"🎯 New High-Match Opportunity ({match_score:.0f}%)",
        body=f"{job_title} at {company}",
        notification_type="job_match",
        data={
            "job_id": job_id,
            "match_score": match_score,
            "action_url": f"/jobs/{job_id}",
        },
    )


async def notify_application_ready(
    job_title: str,
    company: str,
    job_id: int,
):
    """Notify that resume + cover letter are ready for review."""
    await send_notification(
        title="📝 Application Package Ready",
        body=f"Resume & cover letter prepared for {job_title} at {company}",
        notification_type="success",
        data={
            "job_id": job_id,
            "action_url": f"/jobs/{job_id}",
        },
    )


async def notify_application_status(
    job_title: str,
    company: str,
    new_status: str,
    application_id: int,
):
    """Notify about an application status change."""
    status_emojis = {
        "applied": "✅",
        "interview": "🎤",
        "assessment": "📋",
        "offer": "🎉",
        "rejected": "❌",
    }
    emoji = status_emojis.get(new_status, "📌")

    await send_notification(
        title=f"{emoji} Application Update: {new_status.capitalize()}",
        body=f"{job_title} at {company}",
        notification_type="info",
        data={
            "application_id": application_id,
            "status": new_status,
            "action_url": f"/applications",
        },
    )
