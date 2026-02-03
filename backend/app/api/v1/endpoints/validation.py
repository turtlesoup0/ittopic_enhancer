"""Validation API endpoints."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import asyncio

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
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def create_validation(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Create a validation task.

    This will start background processing to validate topics against reference documents.
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

        # Start background task
        background_tasks.add_task(
            _process_validation,
            task_id,
            request.topic_ids,
            request.domain_filter,
        )

        logger.info("validation_created", task_id=task_id, topic_count=len(request.topic_ids))

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


async def _process_validation(
    task_id: str,
    topic_ids: List[str],
    domain_filter: str | None,
):
    """Background task to process validation."""
    from app.db.session import async_session

    try:
        async with async_session() as db:
            task_repo = ValidationTaskRepository(db)
            validation_repo = ValidationRepository(db)
            topic_repo = TopicRepository(db)

            # Update status to processing
            await task_repo.update_status(task_id, "processing")

            matcher = get_matching_service()
            validator = get_validation_engine()

            for i, topic_id in enumerate(topic_ids):
                try:
                    # Fetch topic from database
                    topic = await topic_repo.get_by_id(topic_id)

                    if not topic:
                        logger.warning("topic_not_found", topic_id=topic_id)
                        continue

                    # Find matching references
                    references = await matcher.find_references(
                        topic,
                        top_k=5,
                        domain_filter=domain_filter,
                    )

                    # Validate content
                    validation_result = await validator.validate(topic, references)
                    await validation_repo.create(validation_result)

                    # Update progress
                    await task_repo.update_status(
                        task_id,
                        "processing",
                        progress=int((i + 1) / len(topic_ids) * 100),
                        current=i + 1,
                    )

                except Exception as e:
                    logger.error("validation_topic_failed", topic_id=topic_id, error=str(e))
                    continue

            # Mark as completed
            await task_repo.update_status(task_id, "completed", progress=100)

            logger.info("validation_completed", task_id=task_id)

    except Exception as e:
        logger.error("validation_failed", task_id=task_id, error=str(e))
        async with async_session() as db:
            task_repo = ValidationTaskRepository(db)
            await task_repo.update_status(task_id, "failed", error=str(e))
