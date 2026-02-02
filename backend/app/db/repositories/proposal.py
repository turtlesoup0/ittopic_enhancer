"""Proposal repository for database operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, List

from app.db.models.proposal import ProposalORM
from app.models.proposal import EnhancementProposal


class ProposalRepository:
    """Repository for Proposal database operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._db = db

    async def get_by_id(self, proposal_id: str) -> Optional[EnhancementProposal]:
        """Get proposal by ID."""
        result = await self._db.execute(
            select(ProposalORM).where(ProposalORM.id == proposal_id)
        )
        proposal_orm = result.scalar_one_or_none()
        if not proposal_orm:
            return None
        return self._orm_to_model(proposal_orm)

    async def get_by_topic_id(
        self, topic_id: str, include_applied: bool = False, include_rejected: bool = False
    ) -> List[EnhancementProposal]:
        """Get proposals for a topic."""
        query = select(ProposalORM).where(ProposalORM.topic_id == topic_id)

        if not include_applied:
            query = query.where(ProposalORM.applied == False)
        if not include_rejected:
            query = query.where(ProposalORM.rejected == False)

        result = await self._db.execute(
            query.order_by(ProposalORM.priority.desc(), ProposalORM.created_at.desc())
        )
        proposals_orm = result.scalars().all()
        return [self._orm_to_model(p) for p in proposals_orm]

    async def create(self, proposal: EnhancementProposal) -> EnhancementProposal:
        """Create new proposal."""
        proposal_orm = ProposalORM(
            id=proposal.id,
            topic_id=proposal.topic_id,
            priority=proposal.priority.value,
            title=proposal.title,
            description=proposal.description,
            current_content=proposal.current_content,
            suggested_content=proposal.suggested_content,
            reasoning=proposal.reasoning,
            reference_sources=proposal.reference_sources,
            estimated_effort=proposal.estimated_effort,
            confidence=proposal.confidence,
            applied=proposal.applied,
            rejected=proposal.rejected,
            created_at=proposal.created_at,
        )
        self._db.add(proposal_orm)
        await self._db.flush()
        return self._orm_to_model(proposal_orm)

    async def create_many(
        self, proposals: List[EnhancementProposal]
    ) -> List[EnhancementProposal]:
        """Create multiple proposals."""
        created_proposals = []
        for proposal in proposals:
            created = await self.create(proposal)
            created_proposals.append(created)
        return created_proposals

    async def mark_applied(self, proposal_id: str) -> Optional[EnhancementProposal]:
        """Mark proposal as applied."""
        result = await self._db.execute(
            update(ProposalORM)
            .where(ProposalORM.id == proposal_id)
            .values(applied=True)
            .returning(ProposalORM)
        )
        proposal_orm = result.scalar_one_or_none()
        if not proposal_orm:
            return None
        return self._orm_to_model(proposal_orm)

    async def mark_rejected(self, proposal_id: str) -> Optional[EnhancementProposal]:
        """Mark proposal as rejected."""
        result = await self._db.execute(
            update(ProposalORM)
            .where(ProposalORM.id == proposal_id)
            .values(rejected=True)
            .returning(ProposalORM)
        )
        proposal_orm = result.scalar_one_or_none()
        if not proposal_orm:
            return None
        return self._orm_to_model(proposal_orm)

    async def count_by_topic(
        self, topic_id: str, active_only: bool = True
    ) -> int:
        """Count proposals for a topic."""
        from sqlalchemy import func

        query = select(func.count(ProposalORM.id)).where(
            ProposalORM.topic_id == topic_id
        )

        if active_only:
            query = query.where(ProposalORM.applied == False).where(
                ProposalORM.rejected == False
            )

        result = await self._db.execute(query)
        return result.scalar() or 0

    @staticmethod
    def _orm_to_model(proposal_orm: ProposalORM) -> EnhancementProposal:
        """Convert ORM to Pydantic model."""
        from app.models.proposal import EnhancementProposal, ProposalPriority

        return EnhancementProposal(
            id=proposal_orm.id,
            topic_id=proposal_orm.topic_id,
            priority=ProposalPriority(proposal_orm.priority),
            title=proposal_orm.title,
            description=proposal_orm.description,
            current_content=proposal_orm.current_content,
            suggested_content=proposal_orm.suggested_content,
            reasoning=proposal_orm.reasoning,
            reference_sources=proposal_orm.reference_sources,
            estimated_effort=proposal_orm.estimated_effort,
            confidence=proposal_orm.confidence,
            created_at=proposal_orm.created_at,
            updated_at=proposal_orm.updated_at,
            applied=proposal_orm.applied,
            rejected=proposal_orm.rejected,
        )
