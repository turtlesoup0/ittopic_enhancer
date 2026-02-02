"""Reference repository for database operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List
from datetime import datetime

from app.db.models.reference import ReferenceORM
from app.models.reference import ReferenceDocument, ReferenceCreate, ReferenceSourceType


class ReferenceRepository:
    """Repository for Reference document database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._db = db

    async def get_by_id(self, reference_id: str) -> Optional[ReferenceDocument]:
        """Get reference by ID."""
        result = await self._db.execute(
            select(ReferenceORM).where(ReferenceORM.id == reference_id)
        )
        reference_orm = result.scalar_one_or_none()
        if not reference_orm:
            return None
        return self._orm_to_model(reference_orm)

    async def get_by_file_path(self, file_path: str) -> Optional[ReferenceDocument]:
        """Get reference by file path."""
        result = await self._db.execute(
            select(ReferenceORM).where(ReferenceORM.file_path == file_path)
        )
        reference_orm = result.scalar_one_or_none()
        if not reference_orm:
            return None
        return self._orm_to_model(reference_orm)

    async def list_by_domain(
        self,
        domain: str,
        source_type: Optional[ReferenceSourceType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReferenceDocument]:
        """List references by domain."""
        query = select(ReferenceORM).where(ReferenceORM.domain == domain)

        if source_type:
            # Handle both enum and string values
            source_value = source_type.value if hasattr(source_type, 'value') else source_type
            query = query.where(ReferenceORM.source_type == source_value)

        result = await self._db.execute(
            query.offset(skip).limit(limit).order_by(ReferenceORM.created_at.desc())
        )
        references_orm = result.scalars().all()
        return [self._orm_to_model(r) for r in references_orm]

    async def list_all(
        self,
        source_type: Optional[ReferenceSourceType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReferenceDocument]:
        """List all references."""
        query = select(ReferenceORM)

        if source_type:
            query = query.where(ReferenceORM.source_type == source_type.value)

        result = await self._db.execute(
            query.offset(skip).limit(limit).order_by(ReferenceORM.created_at.desc())
        )
        references_orm = result.scalars().all()
        return [self._orm_to_model(r) for r in references_orm]

    async def create(self, reference_create: ReferenceCreate) -> ReferenceDocument:
        """Create new reference document."""
        import uuid

        reference_orm = ReferenceORM(
            id=str(uuid.uuid4()),
            source_type=reference_create.source_type.value,
            title=reference_create.title,
            content=reference_create.content,
            url=reference_create.url,
            file_path=reference_create.file_path,
            domain=reference_create.domain,
            trust_score=reference_create.trust_score,
            last_updated=datetime.now(),
        )
        self._db.add(reference_orm)
        await self._db.flush()
        return self._orm_to_model(reference_orm)

    async def create_with_embedding(
        self,
        reference_create: ReferenceCreate,
        embedding: List[float],
    ) -> ReferenceDocument:
        """Create new reference document with embedding."""
        import uuid

        reference_orm = ReferenceORM(
            id=str(uuid.uuid4()),
            source_type=reference_create.source_type.value,
            title=reference_create.title,
            content=reference_create.content,
            url=reference_create.url,
            file_path=reference_create.file_path,
            domain=reference_create.domain,
            embedding=embedding,
            trust_score=reference_create.trust_score,
            last_updated=datetime.now(),
        )
        self._db.add(reference_orm)
        await self._db.flush()
        return self._orm_to_model(reference_orm)

    async def update_embedding(
        self, reference_id: str, embedding: List[float]
    ) -> Optional[ReferenceDocument]:
        """Update reference embedding."""
        result = await self._db.execute(
            update(ReferenceORM)
            .where(ReferenceORM.id == reference_id)
            .values(embedding=embedding, last_updated=datetime.now())
            .returning(ReferenceORM)
        )
        reference_orm = result.scalar_one_or_none()
        if not reference_orm:
            return None
        return self._orm_to_model(reference_orm)

    async def delete(self, reference_id: str) -> bool:
        """Delete reference."""
        result = await self._db.execute(
            select(ReferenceORM).where(ReferenceORM.id == reference_id)
        )
        reference_orm = result.scalar_one_or_none()
        if not reference_orm:
            return False

        await self._db.delete(reference_orm)
        return True

    async def count_by_domain(
        self, domain: str, source_type: Optional[ReferenceSourceType] = None
    ) -> int:
        """Count references by domain."""
        query = select(func.count(ReferenceORM.id)).where(ReferenceORM.domain == domain)

        if source_type:
            query = query.where(ReferenceORM.source_type == source_type.value)

        result = await self._db.execute(query)
        return result.scalar() or 0

    async def get_by_ids(
        self, reference_ids: List[str]
    ) -> List[ReferenceDocument]:
        """Get multiple references by IDs."""
        result = await self._db.execute(
            select(ReferenceORM).where(ReferenceORM.id.in_(reference_ids))
        )
        references_orm = result.scalars().all()
        return [self._orm_to_model(r) for r in references_orm]

    @staticmethod
    def _orm_to_model(reference_orm: ReferenceORM) -> ReferenceDocument:
        """Convert ORM to Pydantic model."""
        return ReferenceDocument(
            id=reference_orm.id,
            source_type=ReferenceSourceType(reference_orm.source_type),
            title=reference_orm.title,
            content=reference_orm.content,
            url=reference_orm.url,
            file_path=reference_orm.file_path,
            domain=reference_orm.domain,
            embedding=reference_orm.embedding,
            trust_score=reference_orm.trust_score,
            last_updated=reference_orm.last_updated,
            created_at=reference_orm.created_at,
            updated_at=reference_orm.updated_at,
        )
