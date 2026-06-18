"""
AutoApply — Celery Configuration

Celery app with Redis broker, task routing to separate queues,
and Celery Beat schedule for periodic job discovery.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "employment",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing — each module gets its own queue
    task_routes={
        "app.tasks.discovery.*": {"queue": "discovery"},
        "app.tasks.matching.*": {"queue": "matching"},
        "app.tasks.resume.*": {"queue": "resume"},
        "app.tasks.notification.*": {"queue": "notifications"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # Result expiry (24 hours)
    result_expires=86400,
)

# Auto-discover tasks from app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# ── Celery Beat Schedule (Periodic Tasks) ─────────────────────
celery_app.conf.beat_schedule = {
    # Run job discovery every 30 minutes
    "discover-jobs-greenhouse": {
        "task": "app.tasks.discovery.discover_all_sources",
        "schedule": crontab(minute="*/30"),
        "args": [],
    },
    # Clean up expired/old jobs daily at midnight
    "cleanup-old-jobs": {
        "task": "app.tasks.discovery.cleanup_expired_jobs",
        "schedule": crontab(hour=0, minute=0),
        "args": [],
    },
}
