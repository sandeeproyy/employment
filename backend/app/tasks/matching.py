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


async def _score_new_jobs(user_token: str):
    """Score all unscored jobs against user profile in parallel for a user."""
    import redis
    from app.core.config import settings
    
    # Track scoring active state in Redis per user
    try:
        r = redis.Redis.from_url(settings.redis_url)
        r.set(f"scoring_active:{user_token}", "true", ex=1800)  # expires in 30 minutes in case of crash
    except Exception as e:
        logger.error(f"Failed to set scoring_active in Redis for {user_token}: {e}")
        r = None

    session_factory = get_async_session()
    scored_count = 0

    try:
        async with session_factory() as session:
            # Get user profile scoped to user
            result = await session.execute(
                select(UserProfile).where(UserProfile.user_token == user_token)
            )
            profile = result.scalar_one_or_none()
            if not profile or not profile.resume_structured:
                logger.warning(f"No profile with resume data for user {user_token}. Skipping scoring.")
                return 0

            # Get preferences scoped to user
            result = await session.execute(
                select(UserPreference).where(UserPreference.user_token == user_token)
            )
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

            # Get unscored jobs scoped to user, limit to 50 to respect Gemini rate limits
            result = await session.execute(
                select(Job)
                .where((Job.status == "new") & (Job.user_token == user_token))
                .order_by(Job.discovered_at.desc())
                .limit(50)
            )
            jobs = result.scalars().all()

            if not jobs:
                logger.info(f"No new jobs to score for user {user_token}.")
                return 0

            logger.info(f"⚡ Scoring {len(jobs)} new jobs concurrently for user {user_token}...")
            
            # Use Semaphore to restrict concurrent requests to Gemini to prevent rate limiting (e.g. max 5 concurrently)
            sem = asyncio.Semaphore(5)

            # Copy parameters to avoid accessing session attributes concurrently
            job_data_list = []
            for job in jobs:
                job_data_list.append({
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "description": job.description,
                    "skills_required": job.skills_required or [],
                    "location": job.location,
                    "job_type": job.job_type,
                })

            async def score_single_job_task(jd):
                async with sem:
                    try:
                        breakdown = await score_job(
                            profile=profile.resume_structured,
                            job_title=jd["title"],
                            job_company=jd["company"],
                            job_description=jd["description"],
                            job_skills=jd["skills_required"],
                            job_location=jd["location"],
                            job_type=jd["job_type"],
                            preferences=pref_dict,
                        )
                        return jd["id"], breakdown, None
                    except Exception as ex:
                        logger.error(f"Parallel scoring failed for job {jd['id']}: {ex}")
                        return jd["id"], None, ex

            # Run parallel scoring tasks
            tasks = [score_single_job_task(jd) for jd in job_data_list]
            scoring_results = await asyncio.gather(*tasks)

            # Apply scoring results to DB objects sequentially
            job_map = {job.id: job for job in jobs}
            high_match_jobs = []

            for job_id, breakdown, error in scoring_results:
                job = job_map.get(job_id)
                if not job or error or not breakdown:
                    continue

                try:
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
                    logger.error(f"Saving score failed for job {job_id}: {e}")
                    await session.rollback()
                    continue

            logger.info(f"Finished parallel scoring run for user {user_token}. Scored {scored_count} jobs. {len(high_match_jobs)} high-match queued.")

    finally:
        # Clear scoring active state in Redis per user
        if r:
            try:
                r.delete(f"scoring_active:{user_token}")
            except Exception as e:
                logger.error(f"Failed to delete scoring_active from Redis for user {user_token}: {e}")

    return scored_count


@celery_app.task(name="app.tasks.matching.score_new_jobs", queue="matching")
def score_new_jobs(user_token: str = "default"):
    """Celery task: Score all new/unscored jobs for a user."""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_score_new_jobs(user_token))
        return result
    finally:
        loop.close()
