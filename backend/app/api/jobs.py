"""
AutoApply — Jobs API Routes

Endpoints for listing, filtering, and reviewing discovered jobs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobResponse, JobListResponse

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: float | None = None,
    max_score: float | None = None,
    status: str | None = None,
    source: str | None = None,
    job_type: str | None = None,
    company: str | None = None,
    search: str | None = None,
    strict_preferences: bool = Query(False),
    max_days_old: int | None = Query(14),
    sort_by: str = Query("match_score", regex="^(match_score|discovered_at|company|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """List discovered jobs with filtering, searching, and pagination."""
    import datetime
    from app.models.preference import UserPreference

    # Load preferences
    pref_result = await db.execute(select(UserPreference).limit(1))
    pref = pref_result.scalar_one_or_none()

    query = select(Job)

    # Apply age cutoff filter
    if max_days_old is not None:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=max_days_old)
        if status in ["new", "scored", "reviewed"] or not status:
            query = query.where(Job.discovered_at >= cutoff)

    # Apply strict preferences filter
    if strict_preferences and pref:
        if status in ["new", "scored", "reviewed"] or not status:
            # Filter by job type
            if pref.job_types:
                query = query.where(Job.job_type.in_(pref.job_types))
            
            # Filter by match score
            query = query.where(
                or_(
                    Job.match_score >= pref.min_match_score,
                    Job.status == "new",
                )
            )

            # Filter by location
            if pref.locations:
                loc_filters = []
                for loc in pref.locations:
                    country = loc.get("country")
                    city = loc.get("city")
                    remote_allowed = loc.get("remote_allowed")

                    single_loc_filter = []
                    if country:
                        single_loc_filter.append(Job.location.ilike(f"%{country}%"))
                    if city:
                        single_loc_filter.append(Job.location.ilike(f"%{city}%"))
                    if remote_allowed:
                        single_loc_filter.append(Job.remote_allowed == True)
                        single_loc_filter.append(Job.location.ilike("%remote%"))
                    if single_loc_filter:
                        loc_filters.append(or_(*single_loc_filter))
                if loc_filters:
                    query = query.where(or_(*loc_filters))

            # Filter by domains
            if pref.domains:
                domain_filters = []
                for domain in pref.domains:
                    clean_domain = domain.replace("_", " ")
                    domain_filters.append(Job.title.ilike(f"%{clean_domain}%"))
                    domain_filters.append(Job.description.ilike(f"%{clean_domain}%"))
                if domain_filters:
                    query = query.where(or_(*domain_filters))

    # Apply explicit query filters
    if min_score is not None:
        query = query.where(Job.match_score >= min_score)
    if max_score is not None:
        query = query.where(Job.match_score <= max_score)
    if status:
        query = query.where(Job.status == status)
    if source:
        query = query.where(Job.source == source)
    if job_type:
        query = query.where(Job.job_type == job_type)
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if search:
        query = query.where(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
                Job.company.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort
    sort_column = getattr(Job, sort_by, Job.match_score)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed job information including match breakdown."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Mark as reviewed
    if job.status in ("new", "scored", "notified"):
        job.status = "reviewed"
        await db.flush()

    return job


@router.post("/{job_id}/approve")
async def approve_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a job for application submission."""
    import logging
    import datetime
    from app.models.application import Application
    from app.models.user import UserProfile
    from app.services.resume_tailor import save_tailored_resume
    from app.services.cover_letter import save_cover_letter

    logger = logging.getLogger(__name__)

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job status
    job.status = "approved"

    # Check if application already exists
    app_result = await db.execute(select(Application).where(Application.job_id == job_id))
    app = app_result.scalar_one_or_none()

    if app:
        app.status = "applied"
        app.applied_at = datetime.datetime.utcnow()
    else:
        # Load user profile for resume generation
        profile_result = await db.execute(select(UserProfile).limit(1))
        profile = profile_result.scalar_one_or_none()

        if not profile or not profile.resume_structured:
            raise HTTPException(
                status_code=400,
                detail="User profile or resume not configured. Please upload a resume first."
            )

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

            # Create application record with status applied
            app = Application(
                job_id=job_id,
                tailored_resume_path=resume_path,
                cover_letter_text=cover_letter_text,
                cover_letter_path=cover_letter_path,
                status="applied",
                applied_at=datetime.datetime.utcnow(),
            )
            db.add(app)
        except Exception as e:
            logger.error(f"Failed to prepare application on approval: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to prepare application materials: {str(e)}"
            )

    await db.commit()

    return {"message": f"Job approved: {job.title} @ {job.company}", "status": "approved"}


@router.post("/{job_id}/reject")
async def reject_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a job (won't apply)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "rejected"
    await db.flush()

    return {"message": f"Job rejected: {job.title} @ {job.company}", "status": "rejected"}


@router.post("/trigger-discovery")
async def trigger_discovery():
    """Manually trigger job discovery (useful for testing)."""
    from app.tasks.discovery import discover_all_sources
    task = discover_all_sources.delay()
    return {"message": "Discovery triggered", "task_id": str(task.id)}


@router.post("/trigger-scoring")
async def trigger_scoring():
    """Manually trigger job scoring (useful for testing)."""
    from app.tasks.matching import score_new_jobs
    task = score_new_jobs.delay()
    return {"message": "Scoring triggered", "task_id": str(task.id)}


@router.post("/reset-all")
async def reset_all():
    """Reset the database completely by dropping and recreating all tables, and purging local storage folders."""
    import os
    import shutil
    from app.core.config import settings
    from app.core.database import engine, Base

    # Purge uploads
    upload_dir = settings.upload_path
    if upload_dir.exists():
        for filename in os.listdir(upload_dir):
            file_path = upload_dir / filename
            try:
                if file_path.is_file() or file_path.is_symlink():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except Exception as e:
                pass

    # Purge generated documents
    generated_dir = settings.generated_path
    if generated_dir.exists():
        for filename in os.listdir(generated_dir):
            file_path = generated_dir / filename
            try:
                if file_path.is_file() or file_path.is_symlink():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except Exception as e:
                pass

    # Reset Postgres DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    return {"message": "All data and files successfully reset."}
