"""Validation API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.api.deps import get_db, get_current_request_id
from app.core.api import ApiResponse
from app.core.errors import ErrorCode
from app.models.validation import (
    ValidationRequest,
    ValidationResponse,
    ValidationTaskStatus,
    ValidationResult,
)
from app.models.topic import Topic
from app.models.proposal import EnhancementProposal
from app.db.repositories.validation import ValidationTaskRepository, ValidationRepository
from app.db.repositories.topic import TopicRepository
from app.db.repositories.proposal import ProposalRepository
from app.services.matching.matcher import get_matching_service
from app.services.validation.engine import get_validation_engine
from app.services.proposal.generator import get_proposal_generator
from app.services.llm.worker import process_validation_task
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def create_validation(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Create a validation task.

    This will submit a Celery task for background processing to validate topics
    against reference documents.
    """
    try:
        task_id = f"validation-{uuid.uuid4()}"

        # Create task in database
        task_repo = ValidationTaskRepository(db)
        await task_repo.create(
            task_id=task_id,
            topic_ids=request.topic_ids,
            domain_filter=request.domain_filter,
        )
        await db.commit()

        # Submit Celery task (non-blocking)
        celery_task = process_validation_task.delay(
            task_id=task_id,
            topic_ids=request.topic_ids,
            domain_filter=request.domain_filter,
        )

        logger.info(
            "validation_celery_task_submitted",
            task_id=task_id,
            celery_task_id=celery_task.id,
            topic_count=len(request.topic_ids),
        )

        response_data = ValidationResponse(
            task_id=task_id,
            status="queued",
            estimated_time=len(request.topic_ids) * 30,  # 30 seconds per topic
        )

        return ApiResponse.success_response(
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("create_validation_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="검증 작업 생성 실패",
            request_id=request_id,
        )


@router.get("/task/{task_id}", response_model=ApiResponse)
async def get_validation_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Get validation task status."""
    try:
        task_repo = ValidationTaskRepository(db)
        task = await task_repo.get_by_id(task_id)

        if not task:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="작업을 찾을 수 없습니다",
                details={"task_id": task_id},
                request_id=request_id,
            )

        return ApiResponse.success_response(
            data=task,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("get_validation_status_failed", task_id=task_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="작업 상태 조회 실패",
            details={"task_id": task_id},
            request_id=request_id,
        )


@router.get("/task/{task_id}/result", response_model=ApiResponse)
async def get_validation_result(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Get validation results."""
    try:
        task_repo = ValidationTaskRepository(db)
        task = await task_repo.get_by_id(task_id)

        if not task:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="작업을 찾을 수 없습니다",
                details={"task_id": task_id},
                request_id=request_id,
            )

        if task.status != "completed":
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"작업이 완료되지 않았습니다. 현재 상태: {task.status}",
                details={"task_id": task_id, "status": task.status},
                request_id=request_id,
            )

        results = await task_repo.get_results(task_id)
        return ApiResponse.success_response(
            data=results,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("get_validation_result_failed", task_id=task_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="검증 결과 조회 실패",
            details={"task_id": task_id},
            request_id=request_id,
        )


@router.post("/task/{task_id}/proposals", response_model=ApiResponse)
async def generate_proposals_for_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Generate enhancement proposals for a completed validation task.

    This endpoint generates proposals based on validation results and stores them in the database.
    """
    try:
        task_repo = ValidationTaskRepository(db)
        task = await task_repo.get_by_id(task_id)

        if not task:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="작업을 찾을 수 없습니다",
                details={"task_id": task_id},
                request_id=request_id,
            )

        if task.status != "completed":
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"작업이 완료되지 않았습니다. 현재 상태: {task.status}",
                details={"task_id": task_id, "status": task.status},
                request_id=request_id,
            )

        # Get validation results
        results = await task_repo.get_results(task_id)

        if not results:
            return ApiResponse.success_response(
                data=[],
                request_id=request_id,
            )

        # Generate proposals for each validation result
        proposal_gen = get_proposal_generator()
        topic_repo = TopicRepository(db)
        proposal_repo = ProposalRepository(db)

        all_proposals = []

        for result in results:
            try:
                # Fetch topic to get metadata including exam_frequency
                topic = await topic_repo.get_by_id(result.topic_id)

                # Generate proposals with topic context
                proposals = await proposal_gen.generate_proposals(
                    validation_result=result,
                    topic=topic,
                )

                # Store proposals
                if proposals:
                    await proposal_repo.create_many(proposals)
                    all_proposals.extend(proposals)

                    logger.info(
                        "proposals_generated",
                        topic_id=result.topic_id,
                        proposal_count=len(proposals),
                    )

            except Exception as e:
                logger.error("proposal_generation_failed", topic_id=result.topic_id, error=str(e))
                continue

        return ApiResponse.success_response(
            data=all_proposals,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("generate_proposals_failed", task_id=task_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="제안 생성 실패",
            details={"task_id": task_id},
            request_id=request_id,
        )
