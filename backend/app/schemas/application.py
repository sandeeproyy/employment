"""
Pydantic schemas for application tracking endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ApplicationResponse(BaseModel):
    """Response schema for an application."""
    id: int
    job_id: int
    tailored_resume_path: str | None = None
    cover_letter_text: str | None = None
    cover_letter_path: str | None = None
    status: str
    application_answers: dict | None = None
    notes: str | None = None
    created_at: datetime
    applied_at: datetime | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationWithJob(ApplicationResponse):
    """Application response enriched with job details."""
    job_title: str = ""
    job_company: str = ""
    job_match_score: float = 0


class ApplicationStatusUpdate(BaseModel):
    """Schema for updating application status."""
    status: str  # pending | applied | interview | assessment | offer | rejected


class ApplicationNotesUpdate(BaseModel):
    """Schema for updating application notes."""
    notes: str


class ApplicationAnalytics(BaseModel):
    """Aggregate analytics for applications."""
    total_applied: int = 0
    total_interviews: int = 0
    total_assessments: int = 0
    total_offers: int = 0
    total_rejected: int = 0
    total_pending: int = 0
    response_rate: float = 0.0  # (interviews + offers) / applied * 100
    offer_rate: float = 0.0  # offers / applied * 100


class KanbanColumn(BaseModel):
    """A single Kanban column with its applications."""
    status: str
    label: str
    applications: list[ApplicationWithJob] = Field(default_factory=list)
    count: int = 0


class KanbanBoard(BaseModel):
    """Full Kanban board data."""
    columns: list[KanbanColumn] = Field(default_factory=list)
    analytics: ApplicationAnalytics = Field(default_factory=ApplicationAnalytics)
