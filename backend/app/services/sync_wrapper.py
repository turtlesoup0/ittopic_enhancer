"""
Synchronous wrapper services for async operations in Celery workers.

This module provides synchronous wrappers for async services (matching, validation)
that can be safely called from Celery workers. Each wrapper creates an isolated
event loop for the async operation, avoiding event loop conflicts.
"""
import asyncio
from typing import List
from app.models.topic import Topic
from app.models.reference import MatchedReference
from app.models.validation import ValidationResult


def find_references_sync(
    topic: Topic,
    top_k: int = 5,
    domain_filter: str | None = None,
) -> List[MatchedReference]:
    """
    Synchronous wrapper for finding references.

    Creates a new event loop to run the async matching service.

    Args:
        topic: Topic to find references for
        top_k: Number of top matches to return
        domain_filter: Optional domain filter

    Returns:
        List of matched references
    """
    async def _async_find():
        from app.services.matching.matcher import get_matching_service
        matcher = get_matching_service()
        return await matcher.find_references(topic, top_k=top_k, domain_filter=domain_filter)

    # Run in new event loop (isolated from Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_find())
    finally:
        # Clean up the loop
        loop.close()


def validate_sync(
    topic: Topic,
    references: List[MatchedReference],
) -> ValidationResult:
    """
    Synchronous wrapper for validation.

    Creates a new event loop to run the async validation engine.

    Args:
        topic: Topic to validate
        references: Matched reference documents

    Returns:
        Validation result with gaps and scores
    """
    async def _async_validate():
        from app.services.validation.engine import get_validation_engine
        validator = get_validation_engine()
        return await validator.validate(topic, references)

    # Run in new event loop (isolated from Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_validate())
    finally:
        # Clean up the loop
        loop.close()
