"""
AutoApply — Preferences API Routes

Endpoints for managing job search preferences.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import verify_api_token
from app.models.preference import UserPreference
from app.schemas.preference import PreferenceResponse, PreferenceUpdate

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


@router.get("", response_model=PreferenceResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get current user preferences."""
    result = await db.execute(select(UserPreference).where(UserPreference.user_token == user_token))
    pref = result.scalar_one_or_none()

    if not pref:
        # Create default preferences for this specific user
        pref = UserPreference(user_token=user_token)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return pref


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    data: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Update user preferences."""
    result = await db.execute(select(UserPreference).where(UserPreference.user_token == user_token))
    pref = result.scalar_one_or_none()

    if not pref:
        pref = UserPreference(user_token=user_token)
        db.add(pref)

    if data.job_types is not None:
        pref.job_types = data.job_types
    if data.domains is not None:
        pref.domains = data.domains
    if data.experience_level is not None:
        pref.experience_level = data.experience_level
    if data.locations is not None:
        pref.locations = [loc.model_dump() for loc in data.locations]
    if data.target_companies is not None:
        pref.target_companies = data.target_companies
    if data.min_match_score is not None:
        pref.min_match_score = data.min_match_score
    if data.job_sources is not None:
        pref.job_sources = [src.model_dump() for src in data.job_sources]

    await db.commit()
    await db.refresh(pref)

    # Auto-trigger job discovery/scoring pipeline if resume is uploaded
    from app.services.pipeline_trigger import auto_trigger_pipeline_if_ready
    await auto_trigger_pipeline_if_ready(db, user_token)

    return pref
