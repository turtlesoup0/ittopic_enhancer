"""Topic API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.api.deps import get_db
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


@router.post("/", response_model=Topic)
async def create_topic(
    topic_data: TopicCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new topic."""
    repo = TopicRepository(db)

    # Check if topic already exists by file path
    existing = await repo.get_by_file_path(topic_data.file_path)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Topic with file_path '{topic_data.file_path}' already exists"
        )

    # Create topic in database
    created = await repo.create(topic_data)

    logger.info("topic_created", topic_id=created.id, file_name=topic_data.file_name)
    return created


@router.post("/upload", response_model=dict)
async def upload_topics(
    topics_data: List[TopicCreate],
    db: AsyncSession = Depends(get_db),
):
    """
    Upload Obsidian Dataview JSON export.

    Creates multiple topics in batch from Obsidian export.
    """
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

    return {
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "topic_ids": topic_ids,
    }


@router.get("/", response_model=TopicListResponse)
async def list_topics(
    domain: Optional[DomainEnum] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List topics with pagination and filtering."""
    repo = TopicRepository(db)
    skip = (page - 1) * size

    if domain:
        topics = await repo.list_by_domain(domain.value, skip=skip, limit=size)
        total = await repo.count_by_domain(domain.value)
    else:
        topics = await repo.list_all(skip=skip, limit=size)
        # Get total count (simplified - may not be accurate for large datasets)
        total = len(topics)

    return TopicListResponse(
        topics=topics,
        total=total,
        page=page,
        size=size,
    )


@router.get("/{topic_id}", response_model=Topic)
async def get_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a topic by ID."""
    repo = TopicRepository(db)
    topic = await repo.get_by_id(topic_id)

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return topic


@router.put("/{topic_id}", response_model=Topic)
async def update_topic(
    topic_id: str,
    update_data: TopicUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a topic."""
    repo = TopicRepository(db)
    updated = await repo.update(topic_id, update_data)

    if not updated:
        raise HTTPException(status_code=404, detail="Topic not found")

    logger.info("topic_updated", topic_id=topic_id)
    return updated


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a topic."""
    repo = TopicRepository(db)
    deleted = await repo.delete(topic_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Topic not found")

    logger.info("topic_deleted", topic_id=topic_id)
    return {"success": True, "message": "Topic deleted successfully"}
