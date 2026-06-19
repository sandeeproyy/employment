from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import verify_api_token
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
    user_token: str = Depends(verify_api_token),
):
    """List discovered jobs with filtering, searching, and pagination."""
    import datetime
    from app.models.preference import UserPreference

    # Load preferences scoped to user
    pref_result = await db.execute(select(UserPreference).where(UserPreference.user_token == user_token))
    pref = pref_result.scalar_one_or_none()

    # Scope jobs query to this specific user
    query = select(Job).where(Job.user_token == user_token)

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


@router.get("/export-pdf")
async def export_jobs_pdf(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Export all matching jobs (score >= user preference min_score or status=approved) to a PDF."""
    from weasyprint import HTML
    from app.models.preference import UserPreference

    # Get user preferences scoped to user
    pref_result = await db.execute(select(UserPreference).where(UserPreference.user_token == user_token))
    pref = pref_result.scalar_one_or_none()
    min_score = pref.min_match_score if pref else 70

    # Query matching jobs scoped to user
    jobs_result = await db.execute(
        select(Job)
        .where(
            (Job.user_token == user_token) &
            or_(
                Job.match_score >= min_score,
                Job.status == "approved"
            )
        )
        .order_by(Job.match_score.desc())
    )
    jobs = jobs_result.scalars().all()

    # Formulate a beautiful HTML table representing the matching jobs list
    html_template = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #333;
            margin: 30px;
          }}
          h1 {{
            color: #10b981;
            border-bottom: 2px dashed #1e293b;
            padding-bottom: 10px;
            font-size: 24px;
            margin-bottom: 5px;
          }}
          .subtitle {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 30px;
          }}
          .job-card {{
            margin-bottom: 20px;
            border-bottom: 1px dashed #cbd5e1;
            padding-bottom: 15px;
            page-break-inside: avoid;
          }}
          .job-title {{
            font-size: 16px;
            font-weight: bold;
            color: #0f172a;
            margin-bottom: 5px;
          }}
          .job-meta {{
            font-size: 12px;
            color: #64748b;
            margin-bottom: 10px;
          }}
          .job-desc {{
            font-size: 11px;
            line-height: 1.5;
            color: #334155;
            text-align: justify;
          }}
          .badge {{
            display: inline-block;
            padding: 2px 6px;
            background-color: #10b981;
            color: #05070a;
            font-size: 10px;
            font-weight: bold;
            margin-right: 5px;
          }}
          .badge-score {{
            background-color: #00f0ff;
            color: #05070a;
          }}
        </style>
      </head>
      <body>
        <h1>AutoApply — Matching Jobs Pipeline</h1>
        <div class="subtitle">Exported Pipeline Records • {len(jobs)} records found</div>
    """

    for idx, job in enumerate(jobs):
        score_badge = f'<span class="badge badge-score">Match: {round(job.match_score)}%</span>' if job.match_score else ''
        status_badge = f'<span class="badge">{job.status.upper()}</span>'
        
        # Safe URL formatting
        url_link = f'<a href="{job.apply_url}" target="_blank" style="color: #2980b9; font-weight: bold; text-decoration: underline;">[View Posting]</a>' if job.apply_url else ''
        
        # Truncate description for readability
        desc = job.description[:1000] + "..." if len(job.description) > 1000 else job.description
        # Replace newlines for clean PDF layout
        desc_formatted = desc.replace('\n', '<br/>')
        
        html_template += f"""
        <div class="job-card">
          <div class="job-title">#{idx+1} {job.title} at {job.company}</div>
          <div class="job-meta">
            Location: {job.location} | Type: {job.job_type.upper()} | Source: {job.source.upper()} {url_link} <br/>
            {score_badge} {status_badge}
          </div>
          <div class="job-desc">
            {desc_formatted}
          </div>
        </div>
        """

    html_template += """
      </body>
    </html>
    """

    # Generate PDF bytes using WeasyPrint
    pdf_bytes = HTML(string=html_template).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=matching_jobs.pdf",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get detailed job information including match breakdown."""
    result = await db.execute(select(Job).where((Job.id == job_id) & (Job.user_token == user_token)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Mark as reviewed
    if job.status in ("new", "scored", "notified"):
        job.status = "reviewed"
        await db.flush()

    return job


@router.post("/{job_id}/approve")
async def approve_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Approve a job for application submission."""
    import logging
    import datetime
    from app.models.application import Application
    from app.models.user import UserProfile
    from app.services.resume_tailor import save_tailored_resume
    from app.services.cover_letter import save_cover_letter

    logger = logging.getLogger(__name__)

    result = await db.execute(select(Job).where((Job.id == job_id) & (Job.user_token == user_token)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update job status
    job.status = "approved"

    # Check if application already exists
    app_result = await db.execute(
        select(Application).where((Application.job_id == job_id) & (Application.user_token == user_token))
    )
    app = app_result.scalar_one_or_none()

    if app:
        app.status = "applied"
        app.applied_at = datetime.datetime.utcnow()
    else:
        # Load user profile for resume generation scoped to user
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_token == user_token)
        )
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

            # Create application record with status applied and user_token
            app = Application(
                job_id=job_id,
                user_token=user_token,
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
async def reject_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Reject a job (won't apply)."""
    result = await db.execute(select(Job).where((Job.id == job_id) & (Job.user_token == user_token)))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "rejected"
    await db.flush()

    return {"message": f"Job rejected: {job.title} @ {job.company}", "status": "rejected"}


@router.post("/trigger-discovery")
async def trigger_discovery(user_token: str = Depends(verify_api_token)):
    """Manually trigger job discovery (useful for testing)."""
    from app.tasks.discovery import discover_all_sources
    task = discover_all_sources.delay(user_token)
    return {"message": "Discovery triggered", "task_id": str(task.id)}


@router.post("/trigger-scoring")
async def trigger_scoring(user_token: str = Depends(verify_api_token)):
    """Manually trigger job scoring (useful for testing)."""
    from app.tasks.matching import score_new_jobs
    task = score_new_jobs.delay(user_token)
    return {"message": "Scoring triggered", "task_id": str(task.id)}


@router.post("/reset-all")
async def reset_all(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Reset the database scoped to the current user."""
    import os
    import shutil
    from sqlalchemy import delete
    from app.core.config import settings
    from app.models.application import Application
    from app.models.job import Job
    from app.models.preference import UserPreference
    from app.models.user import UserProfile

    # Delete user-scoped records
    await db.execute(delete(Application).where(Application.user_token == user_token))
    await db.execute(delete(Job).where(Job.user_token == user_token))
    await db.execute(delete(UserPreference).where(UserPreference.user_token == user_token))
    await db.execute(delete(UserProfile).where(UserProfile.user_token == user_token))
    await db.commit()

    # Purge user uploads (prefixed with user_token)
    upload_dir = settings.upload_path
    if upload_dir.exists():
        for filename in os.listdir(upload_dir):
            if filename.startswith(f"{user_token}_"):
                file_path = upload_dir / filename
                try:
                    if file_path.is_file() or file_path.is_symlink():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                except Exception:
                    pass

    # Purge generated documents (prefixed with user_token)
    generated_dir = settings.generated_path
    if generated_dir.exists():
        for filename in os.listdir(generated_dir):
            if filename.startswith(f"{user_token}_"):
                file_path = generated_dir / filename
                try:
                    if file_path.is_file() or file_path.is_symlink():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                except Exception:
                    pass

    return {"message": f"All data and files successfully reset for user {user_token}."}
