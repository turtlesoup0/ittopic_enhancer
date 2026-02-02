"""Reference ORM model."""
from sqlalchemy import String, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.session import Base


class ReferenceORM(Base):
    """Reference document table."""
    __tablename__ = "references"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    domain: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Embedding
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)

    # Trust score
    trust_score: Mapped[float] = mapped_column(Float, default=1.0)

    # Metadata
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
