"""
AutoApply — User Profile Model

Stores the user's resume data (raw + structured), personal info,
and paths to uploaded files. Single-user system — only one row expected.
"""

import datetime
from sqlalchemy import DateTime, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_token: Mapped[str] = mapped_column(String(255), default="default", index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")

    # ── Resume Data ──────────────────────────────────────────
    # Raw text extracted from PDF
    resume_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured JSON: {skills, projects, education, experience, interests}
    resume_structured: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # File paths
    resume_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_latex_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
        return f"<UserProfile(id={self.id}, name='{self.name}')>"
