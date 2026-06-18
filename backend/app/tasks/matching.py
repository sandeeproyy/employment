"""
AutoApply — Job Matching Tasks

Celery tasks that score new jobs against the user profile,
and trigger resume tailoring for high-match jobs.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import Job
from app.models.user import UserProfile
from app.models.preference import UserPreference
from app.services.job_scorer import score_job

logger = logging.getLogger(__name__)


def get_async_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _score_new_jobs():
    """Score all unscored jobs against user profile."""
    session_factory = get_async_session()

    async with session_factory() as session:
        # Get user profile
        result = await session.execute(select(UserProfile).limit(1))
        profile = result.scalar_one_or_none()
        if not profile or not profile.resume_structured:
            logger.warning("No user profile with resume data. Skipping scoring.")
            return 0

        # Get preferences
        result = await session.execute(select(UserPreference).limit(1))
        preferences = result.scalar_one_or_none()
        pref_dict = {}
        if preferences:
            pref_dict = {
                "job_types": preferences.job_types or [],
                "domains": preferences.domains or [],
                "experience_level": preferences.experience_level or "",
                "locations": preferences.locations or [],
                "target_companies": preferences.target_companies or [],
            }

        # Get unscored jobs, limit to 50 to respect Gemini rate limits
        result = await session.execute(
            select(Job).where(Job.status == "new").order_by(Job.discovered_at.desc()).limit(50)
        )
        jobs = result.scalars().all()

        if not jobs:
            logger.info("No new jobs to score.")
            return 0

        logger.info(f"Scoring {len(jobs)} new jobs...")
        scored_count = 0
        high_match_jobs = []

        for job in jobs:
            try:
                breakdown = await score_job(
                    profile=profile.resume_structured,
                    job_title=job.title,
                    job_company=job.company,
                    job_description=job.description,
                    job_skills=job.skills_required or [],
                    job_location=job.location,
                    job_type=job.job_type,
                    preferences=pref_dict,
                )

                job.match_score = breakdown.get("total", 0)
                job.match_breakdown = breakdown
                job.status = "scored"
                job.scored_at = datetime.utcnow()
                
                # Commit incrementally so that changes show up on the dashboard immediately
                await session.commit()
                scored_count += 1

                # Track high-match jobs for resume tailoring
                min_score = preferences.min_match_score if preferences else 70
                if job.match_score >= min_score:
                    high_match_jobs.append(job.id)
                    # Trigger resume tailoring immediately for this high-match job
                    from app.tasks.resume import prepare_application_package
                    prepare_application_package.delay(job.id)

            except Exception as e:
                logger.error(f"Scoring failed for job {job.id}: {e}")
                await session.rollback()
                continue

        logger.info(f"Finished scoring run. Scored {scored_count} jobs. {len(high_match_jobs)} high-match queued for tailoring.")
        return scored_count


@celery_app.task(name="app.tasks.matching.score_new_jobs", queue="matching")
def score_new_jobs():
    """Celery task: Score all new/unscored jobs."""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_score_new_jobs())
        return result
    finally:
        loop.close()
