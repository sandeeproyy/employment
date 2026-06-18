"""
AutoApply — Preferences API Routes

Endpoints for managing job search preferences.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.preference import UserPreference
from app.schemas.preference import PreferenceResponse, PreferenceUpdate

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


@router.get("", response_model=PreferenceResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get current user preferences."""
    result = await db.execute(select(UserPreference).limit(1))
    pref = result.scalar_one_or_none()

    if not pref:
        # Create default preferences
        pref = UserPreference()
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return pref


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    data: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user preferences."""
    result = await db.execute(select(UserPreference).limit(1))
    pref = result.scalar_one_or_none()

    if not pref:
        pref = UserPreference()
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
    return pref
