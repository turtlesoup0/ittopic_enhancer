"""Validation ORM model."""
from sqlalchemy import String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.session import Base


class ValidationORM(Base):
    """Validation result table."""
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String, ForeignKey("topics.id"), nullable=False, index=True)

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    field_completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    content_accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    reference_coverage_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Gaps (stored as JSON)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    matched_references: Mapped[list] = mapped_column(JSON, default=list)

    # Task tracking
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="pending")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    topic = relationship("TopicORM", back_populates="validations")
