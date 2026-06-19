import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserProfile
from app.models.preference import UserPreference

logger = logging.getLogger(__name__)

async def auto_trigger_pipeline_if_ready(db: AsyncSession, user_token: str):
    """
    If a resume is uploaded (profile exists and has structured data)
    AND preferences are fully set (job_types, domains, locations, and experience_level are set),
    then auto-trigger the scanner and scoring daemon in the background for this user.
    """
    try:
        # 1. Check if profile/resume is ready
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_token == user_token)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile or not profile.resume_structured:
            logger.info(f"Auto-trigger skipped for {user_token}: Resume not uploaded or parsed yet.")
            return

        # 2. Check if preferences are set
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_token == user_token)
        )
        pref = pref_result.scalar_one_or_none()
        
        if not pref:
            logger.info(f"Auto-trigger skipped for {user_token}: Preferences record does not exist.")
            return

        # Check if essential preferences are configured and not empty
        if (pref.job_types and len(pref.job_types) > 0 and 
            pref.domains and len(pref.domains) > 0 and 
            pref.locations and len(pref.locations) > 0 and 
            pref.experience_level):
            
            logger.info(f"⚡ Preferences and resume are fully configured for user {user_token}! Auto-triggering discovery & scoring pipeline...")
            
            # Import tasks dynamically to avoid circular dependencies
            from app.tasks.discovery import discover_all_sources
            from app.tasks.matching import score_new_jobs
            
            # Trigger Celery tasks in background for this specific user
            discover_all_sources.delay(user_token)
            score_new_jobs.delay(user_token)
            
    except Exception as e:
        logger.error(f"Failed to auto-trigger pipeline for user {user_token}: {e}")
