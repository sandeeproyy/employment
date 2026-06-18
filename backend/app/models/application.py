"""
AutoApply — Application Tracking Model

Tracks job applications through stages: pending → applied → interview
→ assessment → offer / rejected. Stores tailored resume + cover letter.
"""

import datetime
from sqlalchemy import DateTime, String, Text, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Linked Job ───────────────────────────────────────────
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )

    # ── Generated Documents ──────────────────────────────────
    tailored_resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_letter_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Application Status ───────────────────────────────────
    # pending → applied → interview → assessment → offer → rejected
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)

    # ── Application Answers ──────────────────────────────────
    # Stores any additional Q&A for the application
    application_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── User Notes ───────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    applied_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"
