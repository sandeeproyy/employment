"""
AutoApply — Notification Tasks

Celery tasks that send notifications when new high-match jobs are found
or when application packages are ready for review.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import Job
from app.services.notification import notify_new_job_match, notify_application_ready

logger = logging.getLogger(__name__)


def get_async_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _send_job_notification(job_id: int):
    """Send notification for a new high-match job."""
    session_factory = get_async_session()

    async with session_factory() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Job {job_id} not found for notification")
            return

        await notify_application_ready(
            job_title=job.title,
            company=job.company,
            job_id=job.id,
        )

        logger.info(f"Notification sent for: {job.title} @ {job.company}")


@celery_app.task(
    name="app.tasks.notification.send_job_notification",
    queue="notifications",
)
def send_job_notification(job_id: int):
    """Celery task: Send a notification about a job match."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_send_job_notification(job_id))
    finally:
        loop.close()
