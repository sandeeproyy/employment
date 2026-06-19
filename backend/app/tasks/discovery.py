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


async def _discover_all_sources(user_token: str):
    """Core async logic for job discovery with parallel scanning."""
    import redis
    from app.core.config import settings
    
    # Track scanner active state in Redis per user
    try:
        r = redis.Redis.from_url(settings.redis_url)
        r.set(f"scanner_active:{user_token}", "true", ex=1800)  # expires in 30 minutes in case of crash
    except Exception as e:
        logger.error(f"Failed to set scanner_active in Redis: {e}")
        r = None

    session_factory = get_async_session()
    total_new = 0

    try:
        async with session_factory() as session:
            # Get user preferences for this specific user
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_token == user_token)
            )
            preferences = result.scalar_one_or_none()

            if not preferences:
                logger.warning(f"No preferences found for user {user_token}. Skipping discovery.")
                return 0

            sources_config = preferences.job_sources or []
            if not sources_config:
                logger.info(f"No job sources configured for user {user_token}. Skipping discovery.")
                return 0

            # Collect active sources
            active_sources = []
            for source_config in sources_config:
                if not source_config.get("enabled", True):
                    continue
                source_type = source_config.get("type", "")
                source_class = SOURCE_CLASSES.get(source_type)
                if not source_class:
                    logger.warning(f"Unknown source type: {source_type}")
                    continue
                active_sources.append((source_config, source_class()))

            if not active_sources:
                logger.info(f"No enabled job sources found for user {user_token}. Skipping discovery.")
                return 0

            # 1. Discover jobs concurrently across all enabled sources
            logger.info(f"⚡ Discovering jobs for user {user_token} from {len(active_sources)} sources concurrently...")
            
            async def discover_source_safe(config, source_inst):
                try:
                    jobs = await source_inst.discover(config)
                    return config, jobs, None
                except Exception as ex:
                    logger.error(f"Source [{config.get('type')}] discovery error: {ex}")
                    return config, [], ex

            # Run concurrently using asyncio.gather
            gather_tasks = [discover_source_safe(cfg, inst) for cfg, inst in active_sources]
            discover_results = await asyncio.gather(*gather_tasks)

            # 2. Process results sequentially (to be DB session-safe)
            for config, raw_jobs, error in discover_results:
                if error:
                    continue
                
                source_type = config.get("type", "")
                source_new_count = 0

                try:
                    for raw_job in raw_jobs:
                        canonical_id = generate_canonical_id(
                            raw_job.company, raw_job.title, raw_job.location
                        )

                        # Check if already exists for this specific user
                        existing = await session.execute(
                            select(Job).where((Job.canonical_id == canonical_id) & (Job.user_token == user_token))
                        )
                        existing_job = existing.scalar_one_or_none()

                        if existing_job:
                            # Merge source URL
                            existing_job.all_source_urls = merge_source_urls(
                                existing_job.all_source_urls or [],
                                raw_job.source_url,
                            )
                            continue

                        # Create new job scoped to this user
                        new_job = Job(
                            canonical_id=canonical_id,
                            user_token=user_token,
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
                        source_new_count += 1

                    await session.commit()
                    logger.info(f"Source [{source_type}] for {user_token}: Saved {source_new_count} new jobs out of {len(raw_jobs)} discovered.")

                    # Parallely trigger scoring and listing for this source immediately
                    if source_new_count > 0:
                        from app.tasks.matching import score_new_jobs
                        score_new_jobs.delay(user_token)

                except Exception as e:
                    logger.error(f"Failed to process and commit jobs for source [{source_type}] and user {user_token}: {e}")
                    await session.rollback()

    finally:
        # Clear scanner active state in Redis per user
        if r:
            try:
                r.delete(f"scanner_active:{user_token}")
            except Exception as e:
                logger.error(f"Failed to delete scanner_active from Redis for user {user_token}: {e}")

    return total_new


@celery_app.task(name="app.tasks.discovery.discover_all_sources", queue="discovery")
def discover_all_sources(user_token: str = "default"):
    """Celery task: Run job discovery across all configured sources for a user."""
    logger.info(f"Starting job discovery run for user {user_token}...")
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_discover_all_sources(user_token))
        logger.info(f"Discovery complete for user {user_token}. {result} new jobs found.")
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
