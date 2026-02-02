"""Topic ORM model."""
from sqlalchemy import String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.session import Base


class TopicORM(Base):
    """Topic table."""
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    folder: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Content fields (stored as JSON)
    리드문: Mapped[str] = mapped_column(Text, default="")
    정의: Mapped[str] = mapped_column(Text, default="")
    키워드: Mapped[dict] = mapped_column(JSON, default=list)
    해시태그: Mapped[str] = mapped_column(String, default="")
    암기: Mapped[str] = mapped_column(Text, default="")

    # Completion status
    completion_리드문: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_정의: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_키워드: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_해시태그: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_암기: Mapped[bool] = mapped_column(Boolean, default=False)

    # Validation
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)
    last_validated: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    validation_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    validations = relationship("ValidationORM", back_populates="topic", cascade="all, delete-orphan")
    proposals = relationship("ProposalORM", back_populates="topic", cascade="all, delete-orphan")
