"""
AutoApply — Job Discovery Tasks

Celery tasks that periodically scan configured job sources,
discover new listings, deduplicate, and trigger the matching pipeline.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import Job
from app.models.preference import UserPreference
from app.services.deduplication import generate_canonical_id, merge_source_urls
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource
from app.sources.rss_feed import RSSFeedSource
from app.sources.linkedin import LinkedInSource

logger = logging.getLogger(__name__)

# Source registry
SOURCE_CLASSES = {
    "greenhouse": GreenhouseSource,
    "lever": LeverSource,
    "rss": RSSFeedSource,
    "linkedin": LinkedInSource,
}


def get_async_session():
    """Create an async session for use in Celery tasks."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _discover_all_sources():
    """Core async logic for job discovery."""
    session_factory = get_async_session()

    async with session_factory() as session:
        # Get user preferences (single user)
        result = await session.execute(select(UserPreference).limit(1))
        preferences = result.scalar_one_or_none()

        if not preferences:
            logger.warning("No user preferences found. Skipping discovery.")
            return 0

        sources_config = preferences.job_sources or []
        if not sources_config:
            logger.info("No job sources configured. Skipping discovery.")
            return 0

        total_new = 0

        for source_config in sources_config:
            if not source_config.get("enabled", True):
                continue

            source_type = source_config.get("type", "")
            source_class = SOURCE_CLASSES.get(source_type)

            if not source_class:
                logger.warning(f"Unknown source type: {source_type}")
                continue

            try:
                source = source_class()
                raw_jobs = await source.discover(source_config)

                for raw_job in raw_jobs:
                    # Generate canonical ID for dedup
                    canonical_id = generate_canonical_id(
                        raw_job.company, raw_job.title, raw_job.location
                    )

                    # Check if already exists
                    existing = await session.execute(
                        select(Job).where(Job.canonical_id == canonical_id)
                    )
                    existing_job = existing.scalar_one_or_none()

                    if existing_job:
                        # Merge source URL
                        existing_job.all_source_urls = merge_source_urls(
                            existing_job.all_source_urls or [],
                            raw_job.source_url,
                        )
                        continue

                    # Create new job
                    new_job = Job(
                        canonical_id=canonical_id,
                        title=raw_job.title,
                        company=raw_job.company,
                        description=raw_job.description,
                        location=raw_job.location,
                        remote_allowed=raw_job.remote_allowed,
                        posted_at=raw_job.posted_at,
                        job_type=raw_job.job_type,
                        experience_level=raw_job.experience_level,
                        department=raw_job.department,
                        source=raw_job.source,
                        source_url=raw_job.source_url,
                        apply_url=raw_job.apply_url,
                        all_source_urls=[raw_job.source_url],
                        skills_required=raw_job.skills_required,
                        salary_info=raw_job.salary_info or None,
                        status="new",
                        discovered_at=raw_job.discovered_at,
                        expires_at=raw_job.expires_at,
                    )
                    session.add(new_job)
                    total_new += 1

                await session.commit()

                logger.info(
                    f"Source [{source_type}]: Processed {len(raw_jobs)} jobs, "
                    f"{total_new} new"
                )

            except Exception as e:
                logger.error(f"Source [{source_type}] failed: {e}")
                await session.rollback()
                continue

    # Trigger matching for new jobs
    if total_new > 0:
        from app.tasks.matching import score_new_jobs
        score_new_jobs.delay()

    return total_new


@celery_app.task(name="app.tasks.discovery.discover_all_sources", queue="discovery")
def discover_all_sources():
    """Celery task: Run job discovery across all configured sources."""
    logger.info("Starting job discovery run...")
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_discover_all_sources())
        logger.info(f"Discovery complete. {result} new jobs found.")
        return result
    finally:
        loop.close()


async def _cleanup_expired():
    """Remove jobs older than 60 days or marked as expired."""
    session_factory = get_async_session()
    async with session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(days=60)
        await session.execute(
            delete(Job).where(
                (Job.discovered_at < cutoff) & (Job.status.in_(["new", "rejected"]))
            )
        )
        await session.commit()


@celery_app.task(name="app.tasks.discovery.cleanup_expired_jobs", queue="discovery")
def cleanup_expired_jobs():
    """Celery task: Clean up old/expired job listings."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_cleanup_expired())
        logger.info("Cleanup complete.")
    finally:
        loop.close()
