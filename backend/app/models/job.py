"""
AutoApply — Job Listing Model

Stores discovered job listings with deduplication support,
match scores, and review status tracking.
"""

import datetime
from sqlalchemy import DateTime, String, Text, Integer, Float, JSON, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Deduplication ────────────────────────────────────────
    # Hash of normalized(company + title + location) for dedup
    canonical_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # ── Job Details ──────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(255), default="")
    remote_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_at: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Classification ───────────────────────────────────────
    job_type: Mapped[str] = mapped_column(String(50), default="")  # internship, full-time, etc.
    experience_level: Mapped[str] = mapped_column(String(50), default="")
    department: Mapped[str] = mapped_column(String(255), default="")

    # ── Source Tracking ──────────────────────────────────────
    source: Mapped[str] = mapped_column(String(100))  # greenhouse, lever, rss, career_page
    source_url: Mapped[str] = mapped_column(String(1000))  # Original listing URL
    apply_url: Mapped[str] = mapped_column(String(1000), default="")
    # All URLs where this job was found (for dedup tracking)
    all_source_urls: Mapped[list] = mapped_column(JSON, default=list)

    # ── Extracted Data ───────────────────────────────────────
    skills_required: Mapped[list] = mapped_column(JSON, default=list)
    salary_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Match Scoring ────────────────────────────────────────
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {
    #   "skills": 38,
    #   "projects": 22,
    #   "education": 15,
    #   "location": 10,
    #   "career_goals": 9,
    #   "total": 94,
    #   "matched_skills": ["ROS2", "SLAM", "OpenCV"],
    #   "missing_skills": ["Gazebo"],
    #   "reason": "Strong match due to ..."
    # }

    # ── Review Status ────────────────────────────────────────
    # new → scored → notified → reviewed → approved/rejected
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)

    # ── Timestamps ───────────────────────────────────────────
    discovered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scored_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}', score={self.match_score})>"
