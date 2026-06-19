"""
AutoApply — User Preference Model

Stores job search preferences: job types, domains, experience level,
geographic preferences, target companies, and match score threshold.
"""

import datetime
from sqlalchemy import DateTime, String, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_token: Mapped[str] = mapped_column(String(255), default="default", index=True)

    # ── Job Preferences ──────────────────────────────────────
    # ["internship", "full-time", "research", "contract"]
    job_types: Mapped[list] = mapped_column(
        JSON, default=lambda: ["internship", "full-time"]
    )

    # ["robotics", "computer_vision", "embodied_ai", "mechanical_design", ...]
    domains: Mapped[list] = mapped_column(
        JSON, default=lambda: ["robotics", "computer_vision"]
    )

    # "student" | "graduate" | "entry_level"
    experience_level: Mapped[str] = mapped_column(
        String(50), default="student"
    )

    # ── Geographic Preferences ───────────────────────────────
    # List of location objects:
    # [
    #   {"country": "India", "state": "Assam", "city": "Guwahati", "remote_allowed": true, "radius_km": 50},
    #   {"country": "Singapore", "remote_allowed": true},
    #   {"country": "Germany", "remote_allowed": true}
    # ]
    locations: Mapped[list] = mapped_column(
        JSON, default=lambda: [{"country": "India", "remote_allowed": True}]
    )

    # ── Target Companies ─────────────────────────────────────
    # ["Tesla", "NVIDIA", "Boston Dynamics", ...]
    target_companies: Mapped[list] = mapped_column(
        JSON, default=list
    )

    # ── Notification Threshold ───────────────────────────────
    # Only notify when match score >= this value
    min_match_score: Mapped[int] = mapped_column(Integer, default=70)

    # ── Job Source Configuration ─────────────────────────────
    # List of enabled sources with their config:
    # [
    #   {"type": "greenhouse", "board_token": "tesla", "interval_minutes": 30},
    #   {"type": "lever", "company": "openai", "interval_minutes": 60},
    #   {"type": "rss", "url": "https://...", "interval_minutes": 15}
    # ]
    job_sources: Mapped[list] = mapped_column(
        JSON, default=list
    )

    # ── Timestamps ───────────────────────────────────────────
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, level='{self.experience_level}')>"
