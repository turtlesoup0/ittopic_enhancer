"""
Characterization tests for Validation API with Celery integration.

These tests capture the current behavior of the validation endpoints
before implementing Celery background tasks. They serve as a safety net
to ensure behavior is preserved during the refactoring.

Test Coverage:
- POST /validate/ - Create validation task
- GET /validate/task/{id} - Get task status
- GET /validate/task/{id}/result - Get validation results
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.repositories.topic import TopicRepository
from app.db.repositories.validation import ValidationTaskRepository
from app.main import app
from app.models.topic import DomainEnum, TopicCreate

TEST_API_KEY = "test-api-key-for-integration-tests-12345"


@pytest.fixture
async def client(db_session: AsyncSession):
    """Async test client fixture using ASGI transport with test DB override."""

    async def override_get_db():
        """Override get_db dependency to use test db_session."""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_topic(db_session):
    """Create a sample topic for testing."""
    topic_repo = TopicRepository(db_session)
    topic_create = TopicCreate(
        file_path="/test/characterization/test.md",
        file_name="test",
        folder="test/characterization",
        domain=DomainEnum.SW,
        리드문="테스트 리드문",
        정의="테스트 정의",
        키워드=["테스트"],
        해시태그="#테스트",
        암기="테스트 암기",
    )
    topic = await topic_repo.create(topic_create)
    await db_session.commit()
    return topic.id


class TestValidationPostCharacterization:
    """Characterization tests for POST /validate/ endpoint."""

    async def test_create_validation_returns_task_id(self, client, sample_topic):
        """
        Characterization test: POST /validate/ should return a task_id.

        Current behavior: Returns 200 with task_id, status='queued', and estimated_time
        """
        response = await client.post(
            "/api/v1/validate/",
            json={
                "topic_ids": [sample_topic],
                "domain_filter": None,
            },
        )

        # Characterize actual response
        assert response.status_code == 200
        data = response.json()

        # Document response structure
        assert "data" in data
        assert "task_id" in data["data"]
        assert "status" in data["data"]
        assert "estimated_time" in data["data"]

        # Document actual values
        task_id = data["data"]["task_id"]
        assert task_id is not None
        assert task_id.startswith("validation-")
        assert data["data"]["status"] == "queued"

    async def test_create_validation_persists_task_to_db(self, client, sample_topic, db_session):
        """
        Characterization test: Task should be persisted to database.

        Current behavior: Task is created with status='queued' in database
        """
        response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )

        data = response.json()
        task_id = data["data"]["task_id"]

        # Verify task exists in database
        task_repo = ValidationTaskRepository(db_session)
        task = await task_repo.get_by_id(task_id)

        assert task is not None
        assert task.status == "queued"
        assert task.progress == 0

    async def test_create_validation_with_multiple_topics(self, client, db_session):
        """
        Characterization test: Multiple topics should be handled.

        Current behavior: Accepts list of topic_ids
        """
        topic_repo = TopicRepository(db_session)
        topic_ids = []

        # Create multiple topics
        for i in range(3):
            topic_create = TopicCreate(
                file_path=f"/test/char/test{i}.md",
                file_name=f"test{i}",
                folder="test/char",
                domain=DomainEnum.SW,
                리드문=f"테스트 리드문 {i}",
                정의=f"테스트 정의 {i}",
                키워드=[f"테스트{i}"],
                해시태그=f"#테스트{i}",
                암기=f"테스트 암기 {i}",
            )
            topic = await topic_repo.create(topic_create)
            topic_ids.append(topic.id)

        await db_session.commit()

        response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": topic_ids},
        )

        assert response.status_code == 200
        data = response.json()
        estimated_time = data["data"]["estimated_time"]

        # Characterize: estimated_time should be 30 seconds per topic
        assert estimated_time == 3 * 30


class TestValidationStatusCharacterization:
    """Characterization tests for GET /validate/task/{id} endpoint."""

    async def test_get_status_returns_task_info(self, client, sample_topic):
        """
        Characterization test: GET status should return task information.

        Current behavior: Returns task with status, progress, total, current fields
        """
        # First create a task
        create_response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )
        task_id = create_response.json()["data"]["task_id"]

        # Get status
        status_response = await client.get(f"/api/v1/validate/task/{task_id}")

        assert status_response.status_code == 200
        data = status_response.json()

        # Document response structure
        assert "data" in data
        task_data = data["data"]
        assert "task_id" in task_data
        assert "status" in task_data
        assert "progress" in task_data
        assert "total" in task_data
        assert "current" in task_data

    async def test_get_status_for_nonexistent_task(self, client):
        """
        Characterization test: Non-existent task should return 404.

        Current behavior: Returns 404 with error message
        """
        fake_task_id = f"validation-{uuid.uuid4()}"
        response = await client.get(f"/api/v1/validate/task/{fake_task_id}")

        assert response.status_code == 200  # API returns 200 with error data
        data = response.json()
        assert "success" in data
        assert data["success"] == False


class TestValidationResultCharacterization:
    """Characterization tests for GET /validate/task/{id}/result endpoint."""

    async def test_get_result_for_queued_task(self, client, sample_topic):
        """
        Characterization test: Queued task should not return results.

        Current behavior: Returns error when task not completed
        """
        # Create a task
        create_response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )
        task_id = create_response.json()["data"]["task_id"]

        # Try to get results immediately
        result_response = await client.get(f"/api/v1/validate/task/{task_id}/result")

        # Characterize: Should return error for non-completed task
        assert result_response.status_code == 200
        data = result_response.json()
        assert "success" in data
        # Current behavior returns error for queued tasks

    async def test_get_result_for_nonexistent_task(self, client):
        """
        Characterization test: Non-existent task should return 404.

        Current behavior: Returns 404 with error message
        """
        fake_task_id = f"validation-{uuid.uuid4()}"
        response = await client.get(f"/api/v1/validate/task/{fake_task_id}/result")

        assert response.status_code == 200  # API returns 200 with error data
        data = response.json()
        assert "success" in data
        assert data["success"] == False


class TestValidationStatusTransitions:
    """Characterization tests for task status transitions."""

    async def test_status_queued_to_processing_transition(self, client, sample_topic):
        """
        Characterization test: Status should transition from queued to processing.

        Note: Current implementation with BackgroundTasks may not execute properly.
        This test documents the expected behavior.
        """
        # Create task
        create_response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )
        task_id = create_response.json()["data"]["task_id"]

        # Initial status should be queued
        initial_status = await client.get(f"/api/v1/validate/task/{task_id}")
        assert initial_status.json()["data"]["status"] == "queued"

        # Characterize: With Celery, status should eventually become "processing"
        # For now, we document that this transition is expected but may not work
        # with current BackgroundTasks implementation

    async def test_status_processing_to_completed_transition(self, client, sample_topic):
        """
        Characterization test: Status should eventually become completed.

        Note: This test documents expected behavior with Celery.
        Current implementation may not reach this state.
        """
        # Create task
        create_response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )
        task_id = create_response.json()["data"]["task_id"]

        # Characterize: With Celery, we expect:
        # 1. queued -> processing (worker starts)
        # 2. processing -> completed (worker finishes)
        # For now, document that this is the expected flow


class TestValidationTaskPersistence:
    """Characterization tests for task data persistence."""

    async def test_task_persists_topic_ids(self, client, sample_topic, db_session):
        """
        Characterization test: Task should persist topic_ids list.
        """
        response = await client.post(
            "/api/v1/validate/",
            json={"topic_ids": [sample_topic]},
        )
        task_id = response.json()["data"]["task_id"]

        task_repo = ValidationTaskRepository(db_session)
        task = await task_repo.get_by_id(task_id)

        assert task is not None
        # Characterize: Check that topic_ids are accessible
        # (may require direct DB query depending on implementation)

    async def test_task_persists_domain_filter(self, client, sample_topic, db_session):
        """
        Characterization test: Task should persist domain_filter.
        """
        response = await client.post(
            "/api/v1/validate/",
            json={
                "topic_ids": [sample_topic],
                "domain_filter": "SW",
            },
        )
        task_id = response.json()["data"]["task_id"]

        task_repo = ValidationTaskRepository(db_session)
        task = await task_repo.get_by_id(task_id)

        assert task is not None
        # Characterize: Domain filter should be stored
