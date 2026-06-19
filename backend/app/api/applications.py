"""
AutoApply — Applications API Routes

Endpoints for the Kanban board, application tracking, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.core.auth import verify_api_token
from app.models.application import Application
from app.models.job import Job
from app.schemas.application import (
    ApplicationResponse,
    ApplicationWithJob,
    ApplicationStatusUpdate,
    ApplicationNotesUpdate,
    ApplicationAnalytics,
    KanbanColumn,
    KanbanBoard,
)

router = APIRouter(prefix="/api/applications", tags=["Applications"])

# Kanban column definitions
KANBAN_COLUMNS = [
    {"status": "pending", "label": "Pending Review"},
    {"status": "applied", "label": "Applied"},
    {"status": "interview", "label": "Interview"},
    {"status": "assessment", "label": "Assessment"},
    {"status": "offer", "label": "Offer"},
    {"status": "rejected", "label": "Rejected"},
]


@router.get("/kanban", response_model=KanbanBoard)
async def get_kanban_board(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get the full Kanban board with all applications grouped by status."""
    columns = []

    for col_def in KANBAN_COLUMNS:
        status = col_def["status"]
        result = await db.execute(
            select(Application, Job)
            .join(Job, Application.job_id == Job.id)
            .where((Application.status == status) & (Application.user_token == user_token))
            .order_by(Application.updated_at.desc())
        )
        rows = result.all()

        apps = []
        for app, job in rows:
            app_with_job = ApplicationWithJob(
                id=app.id,
                job_id=app.job_id,
                tailored_resume_path=app.tailored_resume_path,
                cover_letter_text=app.cover_letter_text,
                cover_letter_path=app.cover_letter_path,
                status=app.status,
                application_answers=app.application_answers,
                notes=app.notes,
                created_at=app.created_at,
                applied_at=app.applied_at,
                updated_at=app.updated_at,
                job_title=job.title,
                job_company=job.company,
                job_match_score=job.match_score,
            )
            apps.append(app_with_job)

        columns.append(KanbanColumn(
            status=status,
            label=col_def["label"],
            applications=apps,
            count=len(apps),
        ))

    # Analytics
    analytics = await _get_analytics(db, user_token)

    return KanbanBoard(columns=columns, analytics=analytics)


@router.get("", response_model=list[ApplicationWithJob])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """List all applications with job details."""
    result = await db.execute(
        select(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .where(Application.user_token == user_token)
        .order_by(Application.updated_at.desc())
    )
    rows = result.all()

    return [
        ApplicationWithJob(
            id=app.id,
            job_id=app.job_id,
            tailored_resume_path=app.tailored_resume_path,
            cover_letter_text=app.cover_letter_text,
            cover_letter_path=app.cover_letter_path,
            status=app.status,
            application_answers=app.application_answers,
            notes=app.notes,
            created_at=app.created_at,
            applied_at=app.applied_at,
            updated_at=app.updated_at,
            job_title=job.title,
            job_company=job.company,
            job_match_score=job.match_score,
        )
        for app, job in rows
    ]


@router.get("/analytics", response_model=ApplicationAnalytics)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get aggregate application analytics."""
    return await _get_analytics(db, user_token)


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Get a single application with details."""
    result = await db.execute(
        select(Application).where((Application.id == app_id) & (Application.user_token == user_token))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.put("/{app_id}/status", response_model=ApplicationResponse)
async def update_status(
    app_id: int,
    data: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Update application status (move between Kanban columns)."""
    result = await db.execute(
        select(Application).where((Application.id == app_id) & (Application.user_token == user_token))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    valid_statuses = {"pending", "applied", "interview", "assessment", "offer", "rejected"}
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    app.status = data.status

    # Set applied_at timestamp if moving to "applied"
    if data.status == "applied" and not app.applied_at:
        from datetime import datetime
        app.applied_at = datetime.utcnow()

    await db.flush()
    return app


@router.put("/{app_id}/notes", response_model=ApplicationResponse)
async def update_notes(
    app_id: int,
    data: ApplicationNotesUpdate,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Update application notes."""
    result = await db.execute(
        select(Application).where((Application.id == app_id) & (Application.user_token == user_token))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.notes = data.notes
    await db.flush()
    return app


@router.get("/{app_id}/resume", response_class=HTMLResponse)
async def get_application_resume(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Fetch the tailored HTML resume for this application and return it directly."""
    import os

    result = await db.execute(
        select(Application).where((Application.id == app_id) & (Application.user_token == user_token))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if not app.tailored_resume_path:
        raise HTTPException(status_code=404, detail="Tailored resume not found or generated for this application")

    if not os.path.exists(app.tailored_resume_path):
        raise HTTPException(status_code=404, detail="Tailored resume file not found on the server")

    try:
        with open(app.tailored_resume_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume file: {str(e)}")


@router.get("/{app_id}/latex")
async def get_application_latex(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    user_token: str = Depends(verify_api_token),
):
    """Fetch the tailored LaTeX resume for this application and return it."""
    import os

    result = await db.execute(
        select(Application).where((Application.id == app_id) & (Application.user_token == user_token))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if not app.tailored_resume_path:
        raise HTTPException(status_code=404, detail="Tailored resume not found or generated for this application")

    latex_path = os.path.splitext(app.tailored_resume_path)[0] + ".tex"

    if not os.path.exists(latex_path):
        # Regenerate dynamically if missing
        from app.models.job import Job
        from app.models.user import UserProfile
        from app.services.resume_tailor import basic_tailor, render_resume_latex
        
        job_result = await db.execute(select(Job).where((Job.id == app.job_id) & (Job.user_token == user_token)))
        job = job_result.scalar_one_or_none()
        
        profile_result = await db.execute(select(UserProfile).where(UserProfile.user_token == user_token))
        profile = profile_result.scalar_one_or_none()
        
        if job and profile and profile.resume_structured:
            try:
                tailored = basic_tailor(profile.resume_structured, job.description)
                latex_content = render_resume_latex(tailored)
                with open(latex_path, "w", encoding="utf-8") as f:
                    f.write(latex_content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to regenerate LaTeX resume: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="LaTeX resume file not found and cannot be regenerated (missing job or user profile).")

    try:
        with open(latex_path, "r", encoding="utf-8") as f:
            latex_content = f.read()
        return {"latex": latex_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read LaTeX resume file: {str(e)}")


async def _get_analytics(db: AsyncSession, user_token: str) -> ApplicationAnalytics:
    """Calculate aggregate analytics."""
    result = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.user_token == user_token)
        .group_by(Application.status)
    )
    counts = dict(result.all())

    total_applied = counts.get("applied", 0)
    total_interviews = counts.get("interview", 0)
    total_assessments = counts.get("assessment", 0)
    total_offers = counts.get("offer", 0)
    total_rejected = counts.get("rejected", 0)
    total_pending = counts.get("pending", 0)

    total_submitted = total_applied + total_interviews + total_assessments + total_offers + total_rejected

    response_rate = (
        ((total_interviews + total_offers) / total_submitted * 100)
        if total_submitted > 0
        else 0
    )
    offer_rate = (
        (total_offers / total_submitted * 100)
        if total_submitted > 0
        else 0
    )

    return ApplicationAnalytics(
        total_applied=total_applied,
        total_interviews=total_interviews,
        total_assessments=total_assessments,
        total_offers=total_offers,
        total_rejected=total_rejected,
        total_pending=total_pending,
        response_rate=round(response_rate, 1),
        offer_rate=round(offer_rate, 1),
    )
