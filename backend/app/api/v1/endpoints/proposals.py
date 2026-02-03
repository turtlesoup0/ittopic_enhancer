"""Proposal API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_db, get_current_request_id
from app.core.api import ApiResponse
from app.core.errors import ErrorCode
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


@router.get("/", response_model=ApiResponse)
async def list_proposals(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """List proposals for a topic."""
    try:
        repo = ProposalRepository(db)
        proposals = await repo.get_by_topic_id(
            topic_id, include_applied=False, include_rejected=False
        )

        response_data = ProposalListResponse(
            proposals=proposals,
            total=len(proposals),
            topic_id=topic_id,
        )

        return ApiResponse.success_response(
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("list_proposals_failed", topic_id=topic_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="제안 목록 조회 실패",
            details={"topic_id": topic_id},
            request_id=request_id,
        )


@router.post("/apply", response_model=ApiResponse)
async def apply_proposal(
    request: ProposalApplyRequest,
    db: AsyncSession = Depends(get_db),
    req_id: str = Depends(get_current_request_id),
):
    """
    Apply a proposal to update topic content.

    This will update the topic's content with the suggested changes.
    """
    try:
        repo = ProposalRepository(db)

        # Get proposal
        proposal = await repo.get_by_id(request.proposal_id)
        if not proposal:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="제안을 찾을 수 없습니다",
                details={"proposal_id": request.proposal_id},
                request_id=req_id,
            )

        if proposal.topic_id != request.topic_id:
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="제안이 해당 토픽에 속하지 않습니다",
                details={
                    "proposal_id": request.proposal_id,
                    "topic_id": request.topic_id,
                },
                request_id=req_id,
            )

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

        response_data = ProposalApplyResponse(
            success=True,
            message=f"제안이 적용되었습니다: {proposal.title}",
            updated_content=proposal.suggested_content,
        )

        return ApiResponse.success_response(
            data=response_data,
            request_id=req_id,
        )
    except Exception as e:
        logger.error("apply_proposal_failed", proposal_id=request.proposal_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="제안 적용 실패",
            details={"proposal_id": request.proposal_id},
            request_id=req_id,
        )


@router.post("/{proposal_id}/reject", response_model=ApiResponse)
async def reject_proposal(
    proposal_id: str,
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Reject a proposal."""
    try:
        repo = ProposalRepository(db)

        # Get proposal first to verify
        proposal = await repo.get_by_id(proposal_id)
        if not proposal:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="제안을 찾을 수 없습니다",
                details={"proposal_id": proposal_id},
                request_id=request_id,
            )

        if proposal.topic_id != topic_id:
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="제안이 해당 토픽에 속하지 않습니다",
                details={
                    "proposal_id": proposal_id,
                    "topic_id": topic_id,
                },
                request_id=request_id,
            )

        # Mark as rejected
        await repo.mark_rejected(proposal_id)

        logger.info("proposal_rejected", proposal_id=proposal_id, topic_id=topic_id)

        return ApiResponse.success_response(
            data={"success": True, "message": "제안이 거절되었습니다."},
            request_id=request_id,
        )
    except Exception as e:
        logger.error("reject_proposal_failed", proposal_id=proposal_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="제안 거절 실패",
            details={"proposal_id": proposal_id},
            request_id=request_id,
        )


async def store_proposals(topic_id: str, proposals: List[EnhancementProposal], db: AsyncSession):
    """Store proposals for a topic in database."""
    repo = ProposalRepository(db)
    await repo.create_many(proposals)
