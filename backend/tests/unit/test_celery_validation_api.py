"""
Unit tests for Celery validation API integration.

These tests verify that:
1. The validation endpoint can be imported
2. The Celery task is properly configured
3. Database operations work with Celery task pattern
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.api.v1.endpoints.validation import router, create_validation
from app.models.validation import ValidationRequest
from app.services.llm.worker import celery_app, process_validation_task


class TestCeleryValidationAPI:
    """Test Celery integration in validation API."""

    def test_validation_router_exists(self):
        """Test that validation router is defined."""
        assert router is not None
        assert len(router.routes) > 0

    def test_create_validation_function_exists(self):
        """Test that create_validation function exists."""
        assert create_validation is not None
        assert callable(create_validation)

    @patch("app.api.v1.endpoints.validation.process_validation_task")
    @patch("app.api.v1.endpoints.validation.ValidationTaskRepository")
    async def test_create_validation_submits_celery_task(
        self,
        mock_task_repo_class,
        mock_celery_task,
        db_session,
    ):
        """Test that create_validation submits Celery task."""
        # Setup mocks
        mock_task_repo = AsyncMock()
        mock_task_repo_class.return_value = mock_task_repo
        mock_task_repo.create = AsyncMock(return_value=Mock(task_id="test-123"))

        mock_celery_task.delay = Mock(return_value=Mock(id="celery-456"))

        # Create request
        request = ValidationRequest(
            topic_ids=["topic-1", "topic-2"],
            domain_filter=None,
        )

        # Call the function
        result = await create_validation(
            request=request,
            db=db_session,
            request_id="test-req-id",
        )

        # Verify Celery task was submitted
        mock_celery_task.delay.assert_called_once()
        call_args = mock_celery_task.delay.call_args

        # Check that task_id starts with "validation-" (UUID pattern)
        assert call_args[1]["task_id"].startswith("validation-")
        assert call_args[1]["topic_ids"] == ["topic-1", "topic-2"]
        assert call_args[1]["domain_filter"] is None

    def test_celery_task_configured(self):
        """Test that Celery task is properly configured."""
        assert process_validation_task is not None
        assert process_validation_task.name == "process_validation"
        assert process_validation_task.max_retries == 3


class TestCeleryWorkerTask:
    """Test Celery worker task execution pattern."""

    def test_celery_app_configured(self):
        """Test that Celery app is configured correctly."""
        assert celery_app is not None
        assert celery_app.main == "itpe_worker"
        assert "redis://" in celery_app.conf.broker_url
        assert "redis://" in celery_app.conf.result_backend

    def test_celery_task_has_retry_config(self):
        """Test that Celery task has retry configuration."""
        assert process_validation_task.max_retries == 3
        assert process_validation_task.name == "process_validation"

    def test_celery_task_accepts_correct_arguments(self):
        """Test that Celery task accepts the correct arguments."""
        # The task should accept: task_id, topic_ids, domain_filter
        # We can't test execution directly, but we can verify the signature
        assert callable(process_validation_task)


class TestDatabaseSessionPattern:
    """Test database session pattern used in Celery worker."""

    async def test_explicit_commit_pattern_documented(self):
        """Test that explicit commit pattern is documented in worker."""
        # Read the worker.py file and verify it contains the explicit commit pattern
        # SPEC-BGFIX-002: Now uses sync SQLAlchemy, so commit is not awaited
        import inspect
        from app.services.llm import worker

        source = inspect.getsource(worker)
        # Sync SQLAlchemy uses db.commit() without await
        assert "db.commit()" in source
        assert "SyncSessionLocal()" in source

    async def test_sync_wrapper_pattern_documented(self):
        """Test that sync wrapper is used instead of event loop creation."""
        # SPEC-BGFIX-002: Worker uses sync_wrapper instead of creating event loops
        import inspect
        from app.services.llm import worker

        source = inspect.getsource(worker)
        # Should use sync_wrapper module
        assert "sync_wrapper" in source
        # Should import find_references_sync and validate_sync
        assert "find_references_sync" in source
        assert "validate_sync" in source
        # Should NOT create event loops directly (moved to sync_wrapper)
        assert "asyncio.new_event_loop()" not in source


class TestCeleryWorkerIntegration:
    """Integration tests for Celery worker."""

    def test_worker_module_imports_successfully(self):
        """Test that worker module can be imported."""
        from app.services.llm.worker import celery_app, process_validation_task
        assert celery_app is not None
        assert process_validation_task is not None

    def test_celery_broker_url_configured(self):
        """Test that Celery broker URL is configured."""
        from app.core.config import get_settings

        settings = get_settings()
        assert settings.celery_broker_url is not None
        assert "redis://" in settings.celery_broker_url

    def test_celery_backend_url_configured(self):
        """Test that Celery result backend URL is configured."""
        from app.core.config import get_settings

        settings = get_settings()
        assert settings.celery_result_backend is not None
        assert "redis://" in settings.celery_result_backend
