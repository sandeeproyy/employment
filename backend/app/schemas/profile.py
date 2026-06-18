"""
Pydantic schemas for user profile endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ResumeStructured(BaseModel):
    """Structured data extracted from a resume."""
    skills: list[str] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    """Response schema for user profile."""
    id: int
    name: str
    email: str
    resume_structured: ResumeStructured | None = None
    resume_pdf_path: str | None = None
    resume_latex_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    """Schema for manually updating profile fields."""
    name: str | None = None
    email: str | None = None
    resume_structured: ResumeStructured | None = None


class ResumeUploadResponse(BaseModel):
    """Response after resume upload + parsing."""
    message: str
    profile: ProfileResponse
    parsing_status: str  # "success" | "partial" | "failed"
