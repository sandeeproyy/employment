"""
Pydantic schemas for user preference endpoints.
"""

from pydantic import BaseModel, Field


class LocationPreference(BaseModel):
    """A single geographic location preference."""
    country: str
    state: str | None = None
    city: str | None = None
    remote_allowed: bool = False
    radius_km: int | None = None


class JobSourceConfig(BaseModel):
    """Configuration for a single job source."""
    type: str  # greenhouse | lever | rss | career_page
    # Greenhouse-specific
    board_token: str | None = None
    # Lever-specific
    company: str | None = None
    # RSS-specific
    url: str | None = None
    # LinkedIn-specific
    keywords: str | None = None
    location: str | None = None
    job_type: str | None = None
    # Common
    interval_minutes: int = 30
    enabled: bool = True
    label: str = ""  # Human-readable label


class PreferenceResponse(BaseModel):
    """Response schema for user preferences."""
    id: int
    job_types: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    experience_level: str = "student"
    locations: list[LocationPreference] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)
    min_match_score: int = 70
    job_sources: list[JobSourceConfig] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    """Schema for updating preferences."""
    job_types: list[str] | None = None
    domains: list[str] | None = None
    experience_level: str | None = None
    locations: list[LocationPreference] | None = None
    target_companies: list[str] | None = None
    min_match_score: int | None = None
    job_sources: list[JobSourceConfig] | None = None
