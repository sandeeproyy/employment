"""
AutoApply — Profile API Routes

Endpoints for resume upload, profile viewing, and manual updates.
"""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import verify_api_token
from app.models.user import UserProfile
from app.schemas.profile import ProfileResponse, ProfileUpdate, ResumeUploadResponse
from app.services.resume_parser import parse_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get the user's profile."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_token == user_token))
    profile = result.scalar_one_or_none()

    if not profile:
        # Auto-create empty profile for single-user setup
        profile = UserProfile(user_token=user_token, name="", email="")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


@router.put("", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Manually update profile fields."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_token == user_token))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_token=user_token)
        db.add(profile)

    if data.name is not None:
        profile.name = data.name
    if data.email is not None:
        profile.email = data.email
    if data.resume_structured is not None:
        profile.resume_structured = data.resume_structured.model_dump()

    await db.commit()
    await db.refresh(profile)
    
    # Auto-trigger job discovery/scoring pipeline if preferences are fully set
    from app.services.pipeline_trigger import auto_trigger_pipeline_if_ready
    await auto_trigger_pipeline_if_ready(db, user_token)
    
    return profile


@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """
    Upload a resume PDF. The system will:
    1. Save the file
    2. Extract text using PyMuPDF
    3. Parse structured data using Gemini AI
    4. Store everything in the user profile
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file
    import os
    safe_filename = os.path.basename(file.filename or "resume.pdf")
    upload_path = settings.upload_path / f"{user_token}_{safe_filename}"  # Prefix with user_token to avoid conflicts
    try:
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Parse resume
    parsing_status = "success"
    try:
        raw_text, structured = await parse_resume(str(upload_path))
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raw_text = ""
        structured = {}
        parsing_status = "failed"

    if not structured.get("skills") and not structured.get("experience"):
        parsing_status = "partial"

    # Update or create profile
    result = await db.execute(select(UserProfile).where(UserProfile.user_token == user_token))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_token=user_token)
        db.add(profile)

    profile.resume_raw_text = raw_text
    profile.resume_structured = structured
    profile.resume_pdf_path = str(upload_path)

    # Auto-fill name and email from parsed data
    if structured.get("name"):
        profile.name = structured["name"]
    if structured.get("email"):
        profile.email = structured["email"]

    await db.commit()
    await db.refresh(profile)

    # Auto-trigger job discovery/scoring pipeline if preferences are fully set
    from app.services.pipeline_trigger import auto_trigger_pipeline_if_ready
    await auto_trigger_pipeline_if_ready(db, user_token)

    logger.info(
        f"Resume uploaded for user {user_token}: {file.filename}, "
        f"parsing: {parsing_status}, "
        f"skills: {len(structured.get('skills', []))}"
    )

    return ResumeUploadResponse(
        message=f"Resume uploaded and parsed ({parsing_status})",
        profile=profile,
        parsing_status=parsing_status,
    )
