"""
Celery worker for background validation tasks.

This module provides Celery task execution for validation processing.
Each task runs in a separate worker process using synchronous database access
to avoid event loop conflicts with async database drivers.

Key Changes for SPEC-BGFIX-002:
- Uses sync SQLAlchemy (psycopg2) instead of async (asyncpg)
- Uses sync repositories (ValidationTaskRepositorySync, TopicRepositorySync)
- Uses sync wrapper services for async operations (matching, validation)
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Create Celery app with Redis broker (with password)
celery_app = Celery(
    "itpe_worker",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


@celery_app.task(name="process_validation", bind=True, max_retries=3)
def process_validation_task_sync(
    self,
    task_id: str,
    topic_ids: list[str],
    domain_filter: str | None = None,
):
    """
    Celery task for processing validation using sync SQLAlchemy.

    This task runs in a separate worker process with synchronous database access.
    It uses sync repositories and sync wrapper services to avoid event loop
    conflicts with async database drivers (asyncpg/aiosqlite).

    Key Implementation Details (SPEC-BGFIX-002):
    - Uses SyncSessionLocal from app.db.session
    - Uses ValidationTaskRepositorySync and TopicRepositorySync
    - Uses sync_wrapper functions for async services (matcher, validator)
    - Explicit commit/rollback pattern for transaction management
    - Structured logging with task_id correlation

    Args:
        task_id: Validation task ID
        topic_ids: List of topic IDs to validate
        domain_filter: Optional domain filter for reference matching

    Raises:
        Exception: Re-raises after logging and updating task status to failed
    """
    from app.core.logging import get_logger
    from app.db.repositories.topic_sync import TopicRepositorySync
    from app.db.repositories.validation_sync import (
        ValidationRepositorySync,
        ValidationTaskRepositorySync,
    )
    from app.db.session import SyncSessionLocal
    from app.services.sync_wrapper import find_references_sync, validate_sync

    logger = get_logger(__name__)

    # Use sync session for Celery worker
    db = SyncSessionLocal()

    try:
        # Initialize sync repositories
        task_repo = ValidationTaskRepositorySync(db)
        validation_repo = ValidationRepositorySync(db)
        topic_repo = TopicRepositorySync(db)

        # Update status to processing
        task_repo.update_status(task_id, "processing")
        db.commit()

        logger.info("validation_celery_task_started", task_id=task_id)

        # Process each topic (synchronous)
        for i, topic_id in enumerate(topic_ids):
            try:
                topic = topic_repo.get_by_id(topic_id)
                if not topic:
                    logger.warning("topic_not_found", topic_id=topic_id)
                    continue

                # Find references using sync wrapper
                references = find_references_sync(topic, top_k=5, domain_filter=domain_filter)

                # Validate using sync wrapper
                validation_result = validate_sync(topic, references)
                validation_repo.create(validation_result)

                # Update progress
                task_repo.update_status(
                    task_id,
                    "processing",
                    progress=int((i + 1) / len(topic_ids) * 100),
                    current=i + 1,
                )
                db.commit()

            except Exception as e:
                logger.error(
                    "validation_topic_failed",
                    topic_id=topic_id,
                    error=str(e),
                    exc_info=True,
                )
                db.rollback()
                continue

        # Mark as completed
        task_repo.update_status(task_id, "completed", progress=100)
        db.commit()
        logger.info("validation_celery_task_completed", task_id=task_id)

    except Exception as e:
        logger.error(
            "validation_celery_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        db.rollback()

        # Update status to failed (new session to avoid detached issues)
        db_fail = SyncSessionLocal()
        try:
            task_repo_fail = ValidationTaskRepositorySync(db_fail)
            task_repo_fail.update_status(task_id, "failed", error=str(e))
            db_fail.commit()
        except Exception as update_error:
            logger.error(
                "failed_to_update_error_status",
                task_id=task_id,
                error=str(update_error),
            )
            db_fail.rollback()
        finally:
            db_fail.close()

        raise

    finally:
        db.close()


# Legacy task name for backward compatibility
# During transition, both names point to the same sync implementation
process_validation_task = process_validation_task_sync
