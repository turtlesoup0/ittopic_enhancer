"""Topic API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.api.deps import get_db, get_current_request_id
from app.core.api import ApiResponse
from app.core.errors import ErrorCode
from app.models.topic import (
    Topic,
    TopicCreate,
    TopicUpdate,
    TopicListResponse,
    DomainEnum,
)
from app.db.repositories.topic import TopicRepository
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ApiResponse)
async def create_topic(
    topic_data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Create a new topic."""
    try:
        repo = TopicRepository(db)

        # Check if topic already exists by file path
        existing = await repo.get_by_file_path(topic_data.file_path)
        if existing:
            return ApiResponse.error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"file_path '{topic_data.file_path}'에 대한 토픽이 이미 존재합니다",
                details={"file_path": topic_data.file_path},
                request_id=request_id,
            )

        # Create topic in database
        created = await repo.create(topic_data)

        logger.info("topic_created", topic_id=created.id, file_name=topic_data.file_name)
        return ApiResponse.success_response(
            data=created,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("create_topic_failed", file_path=topic_data.file_path, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 생성 실패",
            details={"file_path": topic_data.file_path},
            request_id=request_id,
        )


@router.post("/upload", response_model=ApiResponse)
async def upload_topics(
    topics_data: List[TopicCreate],
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    Upload Obsidian Dataview JSON export.

    Creates multiple topics in batch from Obsidian export.
    """
    try:
        repo = TopicRepository(db)

        uploaded_count = 0
        failed_count = 0
        topic_ids = []

        for topic_data in topics_data:
            try:
                # Check if topic already exists
                existing = await repo.get_by_file_path(topic_data.file_path)

                if existing:
                    # Update existing topic
                    update_data = TopicUpdate(
                        리드문=topic_data.리드문 or None,
                        정의=topic_data.정의 or None,
                        키워드=topic_data.키워드 or None,
                        해시태그=topic_data.해시태그 or None,
                        암기=topic_data.암기 or None,
                    )
                    updated = await repo.update(existing.id, update_data)
                    if updated:
                        uploaded_count += 1
                        topic_ids.append(updated.id)
                else:
                    # Create new topic
                    created = await repo.create(topic_data)
                    uploaded_count += 1
                    topic_ids.append(created.id)

            except Exception as e:
                logger.error("topic_upload_failed", file_path=topic_data.file_path, error=str(e))
                failed_count += 1
                continue

        logger.info(
            "topics_uploaded",
            uploaded=uploaded_count,
            failed=failed_count,
        )

        return ApiResponse.success_response(
            data={
                "uploaded_count": uploaded_count,
                "failed_count": failed_count,
                "topic_ids": topic_ids,
            },
            request_id=request_id,
        )
    except Exception as e:
        logger.error("upload_topics_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 업로드 실패",
            request_id=request_id,
        )


@router.get("/", response_model=ApiResponse)
async def list_topics(
    domain: Optional[DomainEnum] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """List topics with pagination and filtering."""
    try:
        repo = TopicRepository(db)
        skip = (page - 1) * size

        if domain:
            topics = await repo.list_by_domain(domain.value, skip=skip, limit=size)
            total = await repo.count_by_domain(domain.value)
        else:
            topics = await repo.list_all(skip=skip, limit=size)
            # Get total count (simplified - may not be accurate for large datasets)
            total = len(topics)

        response_data = TopicListResponse(
            topics=topics,
            total=total,
            page=page,
            size=size,
        )

        return ApiResponse.success_response(
            data=response_data,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("list_topics_failed", error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 목록 조회 실패",
            request_id=request_id,
        )


@router.get("/{topic_id}", response_model=ApiResponse)
async def get_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Get a topic by ID."""
    try:
        repo = TopicRepository(db)
        topic = await repo.get_by_id(topic_id)

        if not topic:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="토픽을 찾을 수 없습니다",
                details={"topic_id": topic_id},
                request_id=request_id,
            )

        return ApiResponse.success_response(
            data=topic,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("get_topic_failed", topic_id=topic_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 조회 실패",
            details={"topic_id": topic_id},
            request_id=request_id,
        )


@router.put("/{topic_id}", response_model=ApiResponse)
async def update_topic(
    topic_id: str,
    update_data: TopicUpdate,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Update a topic."""
    try:
        repo = TopicRepository(db)
        updated = await repo.update(topic_id, update_data)

        if not updated:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="토픽을 찾을 수 없습니다",
                details={"topic_id": topic_id},
                request_id=request_id,
            )

        logger.info("topic_updated", topic_id=topic_id)
        return ApiResponse.success_response(
            data=updated,
            request_id=request_id,
        )
    except Exception as e:
        logger.error("update_topic_failed", topic_id=topic_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 업데이트 실패",
            details={"topic_id": topic_id},
            request_id=request_id,
        )


@router.delete("/{topic_id}", response_model=ApiResponse)
async def delete_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """Delete a topic."""
    try:
        repo = TopicRepository(db)
        deleted = await repo.delete(topic_id)

        if not deleted:
            return ApiResponse.error_response(
                code=ErrorCode.NOT_FOUND,
                message="토픽을 찾을 수 없습니다",
                details={"topic_id": topic_id},
                request_id=request_id,
            )

        logger.info("topic_deleted", topic_id=topic_id)
        return ApiResponse.success_response(
            data={"success": True, "message": "Topic deleted successfully"},
            request_id=request_id,
        )
    except Exception as e:
        logger.error("delete_topic_failed", topic_id=topic_id, error=str(e))
        return ApiResponse.error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="토픽 삭제 실패",
            details={"topic_id": topic_id},
            request_id=request_id,
        )
