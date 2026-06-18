"""
AutoApply — Resume & Cover Letter Tasks

Celery tasks that generate tailored resumes and cover letters
for high-match jobs, then notify the user.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import Job
from app.models.application import Application
from app.models.user import UserProfile
from app.services.resume_tailor import save_tailored_resume
from app.services.cover_letter import save_cover_letter

logger = logging.getLogger(__name__)


def get_async_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _prepare_application(job_id: int):
    """Generate tailored resume + cover letter for a specific job."""
    session_factory = get_async_session()

    async with session_factory() as session:
        # Get job
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # Check if application already exists
        result = await session.execute(
            select(Application).where(Application.job_id == job_id)
        )
        if result.scalar_one_or_none():
            logger.info(f"Application already exists for job {job_id}")
            return

        # Get user profile
        result = await session.execute(select(UserProfile).limit(1))
        profile = result.scalar_one_or_none()
        if not profile or not profile.resume_structured:
            logger.error("No user profile for resume generation")
            return

        try:
            # Generate tailored resume
            resume_path = await save_tailored_resume(
                profile.resume_structured,
                job.title,
                job.company,
                job.description,
            )

            # Generate cover letter
            cover_letter_text, cover_letter_path = await save_cover_letter(
                profile.resume_structured,
                job.title,
                job.company,
                job.description,
            )

            # Create application record
            application = Application(
                job_id=job_id,
                tailored_resume_path=resume_path,
                cover_letter_text=cover_letter_text,
                cover_letter_path=cover_letter_path,
                status="pending",
            )
            session.add(application)

            # Update job status
            job.status = "notified"

            await session.commit()

            logger.info(
                f"Application package ready: {job.title} @ {job.company} "
                f"(score: {job.match_score})"
            )

            # Send notification
            from app.tasks.notification import send_job_notification
            send_job_notification.delay(job_id)

        except Exception as e:
            logger.error(f"Application prep failed for job {job_id}: {e}")
            await session.rollback()


@celery_app.task(
    name="app.tasks.resume.prepare_application_package",
    queue="resume",
)
def prepare_application_package(job_id: int):
    """Celery task: Generate tailored resume + cover letter for a job."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_prepare_application(job_id))
    finally:
        loop.close()
