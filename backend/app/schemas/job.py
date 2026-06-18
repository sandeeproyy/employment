"""
Pydantic schemas for job listing endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class MatchBreakdown(BaseModel):
    """Detailed match scoring breakdown."""
    skills: float = 0
    projects: float = 0
    education: float = 0
    location: float = 0
    career_goals: float = 0
    total: float = 0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reason: str = ""


class JobResponse(BaseModel):
    """Response schema for a job listing."""
    id: int
    canonical_id: str
    title: str
    company: str
    description: str
    location: str
    remote_allowed: bool
    posted_at: str | None = None
    job_type: str
    experience_level: str
    department: str
    source: str
    source_url: str
    apply_url: str
    all_source_urls: list[str] = Field(default_factory=list)
    skills_required: list[str] = Field(default_factory=list)
    salary_info: str | None = None
    match_score: float
    match_breakdown: MatchBreakdown | None = None
    status: str
    discovered_at: datetime
    expires_at: datetime | None = None
    scored_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobFilters(BaseModel):
    """Query filters for job listing."""
    min_score: float | None = None
    max_score: float | None = None
    status: str | None = None
    source: str | None = None
    job_type: str | None = None
    company: str | None = None
    search: str | None = None  # Full-text search on title/description
    page: int = 1
    page_size: int = 20
