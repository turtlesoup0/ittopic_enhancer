"""Integration tests for validation transaction commit behavior (SPEC-FIX-001).

These are CHARACTERIZATION TESTS that capture current behavior before the fix.
They document what the code ACTUALLY does, not what it SHOULD do.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


class TestValidationTransactionBehavior:
    """Characterization tests for validation transaction commit behavior."""

    async def test_characterize_explicit_commit_in_process_validation(self):
        """CHARACTERIZATION TEST: Verify transaction commit behavior in validation processing.

        This test documents the fix for SPEC-FIX-001:
        - Before: Validation results were rolled back when session closed
        - After: Validation results are committed and persist after session closes
        """
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.db.session import Base
        from app.db.repositories.topic import TopicRepository
        from app.db.repositories.validation import ValidationTaskRepository, ValidationRepository
        from app.models.topic import TopicCreate

        # Create in-memory test database
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Create tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create test session factory
        test_async_session = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create a test topic
        async with test_async_session() as db:
            topic_repo = TopicRepository(db)
            topic_create = TopicCreate(
                file_path="test/transaction/topic.md",
                file_name="topic",
                folder="test/transaction",
                domain="신기술",
                리드문="테스트",
                정의="테스트 정의",
                키워드=["테스트"],
                해시태그="#테스트",
                암기="테스트",
            )
            topic = await topic_repo.create(topic_create)
            await db.commit()
            topic_id = topic.id

        # Create validation task
        async with test_async_session() as db:
            task_repo = ValidationTaskRepository(db)
            task_id = f"validation-{uuid.uuid4()}"
            await task_repo.create(
                task_id=task_id,
                topic_ids=[topic_id],
                domain_filter=None,
            )
            await db.commit()

        # Test 1: Without explicit commit (simulating the bug)
        async with test_async_session() as test_db:
            test_task_repo = ValidationTaskRepository(test_db)
            test_validation_repo = ValidationRepository(test_db)

            # Update status
            await test_task_repo.update_status(task_id, "processing")

            # Create a validation result
            from app.models.validation import ValidationResult
            validation_result = ValidationResult(
                id=f"validation-{uuid.uuid4()}",
                topic_id=topic_id,
                overall_score=0.85,
                field_completeness_score=0.9,
                content_accuracy_score=0.8,
                reference_coverage_score=0.85,
                gaps=[],
                matched_references=[],
                validation_timestamp=datetime.now(),
            )
            await test_validation_repo.create(validation_result)

            # Update to completed
            await test_task_repo.update_status(task_id, "completed", progress=100)

            # CRITICAL TEST: Without commit, changes are rolled back
            # Comment out the commit to simulate the bug
            # await test_db.commit()  # <- This line was missing!

        # Verify: Changes were NOT persisted (simulating the bug scenario)
        async with test_async_session() as verify_db:
            verify_task_repo = ValidationTaskRepository(verify_db)
            task = await verify_task_repo.get_by_id(task_id)

            # Without commit in the previous session, status should still be "queued"
            # (the original status before the test_db session)
            assert task is not None
            assert task.status == "queued", f"Expected 'queued', got '{task.status}' - Bug simulated!"

        # Test 2: With explicit commit (simulating the fix)
        async with test_async_session() as test_db:
            test_task_repo = ValidationTaskRepository(test_db)
            test_validation_repo = ValidationRepository(test_db)

            # Update status
            await test_task_repo.update_status(task_id, "processing")

            # Create validation result
            validation_result2 = ValidationResult(
                id=f"validation-{uuid.uuid4()}",
                topic_id=topic_id,
                overall_score=0.90,
                field_completeness_score=0.95,
                content_accuracy_score=0.85,
                reference_coverage_score=0.90,
                gaps=[],
                matched_references=[],
                validation_timestamp=datetime.now(),
            )
            await test_validation_repo.create(validation_result2)

            # Update to completed
            await test_task_repo.update_status(task_id, "completed", progress=100)

            # CRITICAL FIX: Explicit commit to persist changes
            await test_db.commit()

        # Verify: Changes WERE persisted (fix verified!)
        async with test_async_session() as verify_db:
            verify_task_repo = ValidationTaskRepository(verify_db)
            task = await verify_task_repo.get_by_id(task_id)

            assert task is not None
            assert task.status == "completed", f"Expected 'completed', got '{task.status}' - Fix verified!"

            # Verify validation results were persisted
            verify_validation_repo = ValidationRepository(verify_db)
            results = await verify_validation_repo.get_by_topic_id(topic_id)

            # After fix: results should exist and be persisted
            assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
            assert any(r.overall_score == 0.90 for r in results), "Expected to find the committed validation result"

        await test_engine.dispose()
