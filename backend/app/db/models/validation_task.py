"""Validation Task ORM model."""
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.session import Base


class ValidationTaskORM(Base):
    """Validation task table for tracking async validation jobs."""
    __tablename__ = "validation_tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="queued"
    )  # queued, processing, completed, failed

    # Progress tracking
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    total: Mapped[int] = mapped_column(Integer, default=1)
    current: Mapped[int] = mapped_column(Integer, default=0)

    # Error tracking
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request metadata
    topic_ids: Mapped[str] = mapped_column(String, nullable=False)  # JSON string
    domain_filter: Mapped[str | None] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
