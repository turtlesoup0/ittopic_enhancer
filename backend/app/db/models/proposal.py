"""Proposal ORM model."""
from sqlalchemy import String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.session import Base


class ProposalORM(Base):
    """Enhancement proposal table."""
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic_id: Mapped[str] = mapped_column(String, ForeignKey("topics.id"), nullable=False, index=True)

    # Priority
    priority: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Content
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    current_content: Mapped[str] = mapped_column(Text, default="")
    suggested_content: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="")

    # References
    reference_sources: Mapped[list] = mapped_column(JSON, default=list)

    # Metadata
    estimated_effort: Mapped[int] = mapped_column(default=15)  # minutes
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    # Status
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    topic = relationship("TopicORM", back_populates="proposals")
