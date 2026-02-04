"""
Synchronous topic repository for Celery workers.

This module provides synchronous versions of the topic repository methods
for use in Celery workers where async database operations are not compatible.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional, List
import json

from app.db.models.topic import TopicORM
from app.models.topic import Topic, TopicCreate, TopicUpdate


class TopicRepositorySync:
    """Synchronous repository for Topic database operations."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session."""
        self._db = db

    def get_by_id(self, topic_id: str) -> Optional[Topic]:
        """Get topic by ID."""
        result = self._db.execute(
            select(TopicORM).where(TopicORM.id == topic_id)
        )
        topic_orm = result.scalar_one_or_none()
        if not topic_orm:
            return None
        return self._orm_to_model(topic_orm)

    def get_by_file_path(self, file_path: str) -> Optional[Topic]:
        """Get topic by file path."""
        result = self._db.execute(
            select(TopicORM).where(TopicORM.file_path == file_path)
        )
        topic_orm = result.scalar_one_or_none()
        if not topic_orm:
            return None
        return self._orm_to_model(topic_orm)

    def list_by_domain(
        self, domain: str, skip: int = 0, limit: int = 100
    ) -> List[Topic]:
        """List topics by domain."""
        result = self._db.execute(
            select(TopicORM)
            .where(TopicORM.domain == domain)
            .offset(skip)
            .limit(limit)
        )
        topics_orm = result.scalars().all()
        return [self._orm_to_model(t) for t in topics_orm]

    def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[Topic]:
        """List all topics."""
        result = self._db.execute(
            select(TopicORM).offset(skip).limit(limit)
        )
        topics_orm = result.scalars().all()
        return [self._orm_to_model(t) for t in topics_orm]

    def create(self, topic_create: TopicCreate) -> Topic:
        """Create new topic."""
        topic_id = topic_create.file_path.replace("/", "_").replace(".", "_")

        topic_orm = TopicORM(
            id=topic_id,
            file_path=topic_create.file_path,
            file_name=topic_create.file_name,
            folder=topic_create.folder,
            domain=topic_create.domain,
            리드문=topic_create.리드문,
            정의=topic_create.정의,
            키워드=topic_create.키워드,
            해시태그=topic_create.해시태그,
            암기=topic_create.암기,
        )
        self._db.add(topic_orm)
        self._db.flush()
        return self._orm_to_model(topic_orm)

    def update(
        self, topic_id: str, topic_update: TopicUpdate
    ) -> Optional[Topic]:
        """Update topic."""
        result = self._db.execute(
            select(TopicORM).where(TopicORM.id == topic_id)
        )
        topic_orm = result.scalar_one_or_none()
        if not topic_orm:
            return None

        update_data = topic_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(topic_orm, key, value)

        self._db.flush()
        return self._orm_to_model(topic_orm)

    def delete(self, topic_id: str) -> bool:
        """Delete topic."""
        result = self._db.execute(
            select(TopicORM).where(TopicORM.id == topic_id)
        )
        topic_orm = result.scalar_one_or_none()
        if not topic_orm:
            return False

        self._db.delete(topic_orm)
        return True

    def count_by_domain(self, domain: str) -> int:
        """Count topics by domain."""
        result = self._db.execute(
            select(func.count(TopicORM.id)).where(TopicORM.domain == domain)
        )
        return result.scalar() or 0

    @staticmethod
    def _orm_to_model(topic_orm: TopicORM) -> Topic:
        """Convert ORM to Pydantic model."""
        from app.models.topic import (
            Topic,
            TopicMetadata,
            TopicContent,
            TopicCompletionStatus,
        )

        return Topic(
            id=topic_orm.id,
            metadata=TopicMetadata(
                file_path=topic_orm.file_path,
                file_name=topic_orm.file_name,
                folder=topic_orm.folder,
                domain=topic_orm.domain,
            ),
            content=TopicContent(
                리드문=topic_orm.리드문,
                정의=topic_orm.정의,
                키워드=topic_orm.키워드 if isinstance(topic_orm.키워드, list) else [],
                해시태그=topic_orm.해시태그,
                암기=topic_orm.암기,
            ),
            completion=TopicCompletionStatus(
                리드문=topic_orm.completion_리드문,
                정의=topic_orm.completion_정의,
                키워드=topic_orm.completion_키워드,
                해시태그=topic_orm.completion_해시태그,
                암기=topic_orm.completion_암기,
            ),
            embedding=topic_orm.embedding,
            last_validated=topic_orm.last_validated,
            validation_score=topic_orm.validation_score,
            created_at=topic_orm.created_at,
            updated_at=topic_orm.updated_at,
        )
