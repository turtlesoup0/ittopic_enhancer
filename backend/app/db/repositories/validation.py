"""Validation repository for database operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, List
import json
from datetime import datetime

from app.db.models.validation import ValidationORM
from app.db.models.validation_task import ValidationTaskORM
from app.models.validation import ValidationResult, ValidationTaskStatus


class ValidationRepository:
    """Repository for Validation result database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._db = db

    async def get_by_id(self, validation_id: str) -> Optional[ValidationResult]:
        """Get validation result by ID."""
        result = await self._db.execute(
            select(ValidationORM).where(ValidationORM.id == validation_id)
        )
        validation_orm = result.scalar_one_or_none()
        if not validation_orm:
            return None
        return self._orm_to_model(validation_orm)

    async def get_by_topic_id(self, topic_id: str) -> List[ValidationResult]:
        """Get all validation results for a topic."""
        result = await self._db.execute(
            select(ValidationORM)
            .where(ValidationORM.topic_id == topic_id)
            .order_by(ValidationORM.created_at.desc())
        )
        validations_orm = result.scalars().all()
        return [self._orm_to_model(v) for v in validations_orm]

    async def create(self, validation: ValidationResult) -> ValidationResult:
        """Create new validation result."""
        # Convert Pydantic models to dict, handling datetime serialization
        gaps_data = []
        for g in validation.gaps:
            gap_dict = g.model_dump()
            # Remove datetime fields if present
            gap_dict.pop('created_at', None)
            gap_dict.pop('updated_at', None)
            gaps_data.append(gap_dict)

        refs_data = []
        for r in validation.matched_references:
            ref_dict = {
                'reference_id': r.reference_id,
                'title': r.title,
                'source_type': r.source_type.value if hasattr(r.source_type, 'value') else r.source_type,
                'similarity_score': r.similarity_score,
                'domain': r.domain,
                'trust_score': r.trust_score,
                'relevant_snippet': r.relevant_snippet,
            }
            refs_data.append(ref_dict)

        validation_orm = ValidationORM(
            id=validation.id,
            topic_id=validation.topic_id,
            overall_score=validation.overall_score,
            field_completeness_score=validation.field_completeness_score,
            content_accuracy_score=validation.content_accuracy_score,
            reference_coverage_score=validation.reference_coverage_score,
            gaps=gaps_data,
            matched_references=refs_data,
            task_id=validation.id.split("-")[0] if "-" in validation.id else "unknown",
            status="completed",
        )
        self._db.add(validation_orm)
        await self._db.flush()
        return validation

    async def get_latest_by_topic(
        self, topic_id: str
    ) -> Optional[ValidationResult]:
        """Get latest validation result for a topic."""
        result = await self._db.execute(
            select(ValidationORM)
            .where(ValidationORM.topic_id == topic_id)
            .order_by(ValidationORM.created_at.desc())
            .limit(1)
        )
        validation_orm = result.scalar_one_or_none()
        if not validation_orm:
            return None
        return self._orm_to_model(validation_orm)

    @staticmethod
    def _orm_to_model(validation_orm: ValidationORM) -> ValidationResult:
        """Convert ORM to Pydantic model."""
        from app.models.validation import ValidationResult, ContentGap

        gaps = [
            ContentGap(**g) if isinstance(g, dict) else g
            for g in validation_orm.gaps
        ]

        return ValidationResult(
            id=validation_orm.id,
            topic_id=validation_orm.topic_id,
            overall_score=validation_orm.overall_score,
            gaps=gaps,
            matched_references=validation_orm.matched_references,
            validation_timestamp=validation_orm.created_at,
            field_completeness_score=validation_orm.field_completeness_score,
            content_accuracy_score=validation_orm.content_accuracy_score,
            reference_coverage_score=validation_orm.reference_coverage_score,
            created_at=validation_orm.created_at,
            updated_at=validation_orm.updated_at,
        )


class ValidationTaskRepository:
    """Repository for Validation Task database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._db = db

    async def get_by_id(self, task_id: str) -> Optional[ValidationTaskStatus]:
        """Get task by ID."""
        result = await self._db.execute(
            select(ValidationTaskORM).where(ValidationTaskORM.task_id == task_id)
        )
        task_orm = result.scalar_one_or_none()
        if not task_orm:
            return None
        return self._orm_to_model(task_orm)

    async def create(
        self,
        task_id: str,
        topic_ids: List[str],
        domain_filter: Optional[str] = None,
    ) -> ValidationTaskStatus:
        """Create new validation task."""
        task_orm = ValidationTaskORM(
            task_id=task_id,
            status="queued",
            progress=0,
            total=len(topic_ids),
            current=0,
            topic_ids=json.dumps(topic_ids),
            domain_filter=domain_filter,
        )
        self._db.add(task_orm)
        await self._db.flush()
        return self._orm_to_model(task_orm)

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        current: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[ValidationTaskStatus]:
        """Update task status."""
        update_values = {"status": status}
        if progress is not None:
            update_values["progress"] = progress
        if current is not None:
            update_values["current"] = current
        if error is not None:
            update_values["error"] = error
        if status == "completed":
            update_values["completed_at"] = datetime.now()

        result = await self._db.execute(
            update(ValidationTaskORM)
            .where(ValidationTaskORM.task_id == task_id)
            .values(**update_values)
            .returning(ValidationTaskORM)
        )
        task_orm = result.scalar_one_or_none()
        if not task_orm:
            return None
        return self._orm_to_model(task_orm)

    async def add_result(
        self, task_id: str, validation: ValidationResult
    ) -> None:
        """Add validation result to task."""
        # Store validation result in validations table
        validation_repo = ValidationRepository(self._db)
        await validation_repo.create(validation)

    async def get_results(self, task_id: str) -> List[ValidationResult]:
        """Get all results for a task."""
        result = await self._db.execute(
            select(ValidationORM)
            .where(ValidationORM.task_id == task_id)
            .order_by(ValidationORM.created_at.desc())
        )
        validations_orm = result.scalars().all()
        return [ValidationRepository._orm_to_model(v) for v in validations_orm]

    @staticmethod
    def _orm_to_model(task_orm: ValidationTaskORM) -> ValidationTaskStatus:
        """Convert ORM to Pydantic model."""
        topic_ids = (
            json.loads(task_orm.topic_ids)
            if isinstance(task_orm.topic_ids, str)
            else task_orm.topic_ids
        )

        return ValidationTaskStatus(
            task_id=task_orm.task_id,
            status=task_orm.status,
            progress=task_orm.progress,
            total=task_orm.total,
            current=task_orm.current,
            error=task_orm.error,
            results=None,  # Results fetched separately
        )
