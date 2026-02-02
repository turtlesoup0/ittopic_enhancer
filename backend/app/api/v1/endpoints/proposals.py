"""Proposal API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_db
from app.models.proposal import (
    ProposalListResponse,
    ProposalApplyRequest,
    ProposalApplyResponse,
    EnhancementProposal,
)
from app.db.repositories.proposal import ProposalRepository
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=ProposalListResponse)
async def list_proposals(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List proposals for a topic."""
    repo = ProposalRepository(db)
    proposals = await repo.get_by_topic_id(
        topic_id, include_applied=False, include_rejected=False
    )

    return ProposalListResponse(
        proposals=proposals,
        total=len(proposals),
        topic_id=topic_id,
    )


@router.post("/apply", response_model=ProposalApplyResponse)
async def apply_proposal(
    request: ProposalApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a proposal to update topic content.

    This will update the topic's content with the suggested changes.
    """
    repo = ProposalRepository(db)

    # Get proposal
    proposal = await repo.get_by_id(request.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.topic_id != request.topic_id:
        raise HTTPException(status_code=400, detail="Proposal does not belong to this topic")

    # Mark as applied
    updated_proposal = await repo.mark_applied(request.proposal_id)

    # TODO: Update topic in database
    # For now, just return success

    logger.info(
        "proposal_applied",
        proposal_id=request.proposal_id,
        topic_id=request.topic_id,
        field=proposal.title,
    )

    return ProposalApplyResponse(
        success=True,
        message=f"제안이 적용되었습니다: {proposal.title}",
        updated_content=proposal.suggested_content,
    )


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposal."""
    repo = ProposalRepository(db)

    # Get proposal first to verify
    proposal = await repo.get_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.topic_id != topic_id:
        raise HTTPException(status_code=400, detail="Proposal does not belong to this topic")

    # Mark as rejected
    await repo.mark_rejected(proposal_id)

    logger.info("proposal_rejected", proposal_id=proposal_id, topic_id=topic_id)

    return {"success": True, "message": "제안이 거절되었습니다."}


async def store_proposals(topic_id: str, proposals: List[EnhancementProposal], db: AsyncSession):
    """Store proposals for a topic in database."""
    repo = ProposalRepository(db)
    await repo.create_many(proposals)
