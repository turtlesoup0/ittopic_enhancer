"""Error categories and exception hierarchy for resilience."""
from typing import Any, Optional
from enum import Enum


class ErrorCategory(Enum):
    """Error category for handling decisions."""

    TRANSIENT = "transient"  # Retry 가능한 일시적 오류
    PERMANENT = "permanent"  # 즉시 실패해야 하는 영구적 오류
    DEGRADED = "degraded"    # Fallback 사용 가능한 성능 저하 오류


class BaseServiceError(Exception):
    """Base exception for all service errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        service: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize service error.

        Args:
            message: Error message
            category: Error category for handling
            service: Service name (e.g., "openai", "chromadb", "embedding")
            operation: Operation being performed (e.g., "chat.completions.create")
            topic_id: Optional topic ID for context
            details: Additional error details
            original_error: Original exception that caused this error
        """
        self.message = message
        self.category = category
        self.service = service
        self.operation = operation
        self.topic_id = topic_id
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "service": self.service,
            "operation": self.operation,
            "topic_id": self.topic_id,
            "details": self.details,
        }


class TransientError(BaseServiceError):
    """Retry 가능한 일시적 오류."""

    def __init__(
        self,
        message: str,
        service: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TRANSIENT,
            service=service,
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


class PermanentError(BaseServiceError):
    """즉시 실패해야 하는 영구적 오류."""

    def __init__(
        self,
        message: str,
        service: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.PERMANENT,
            service=service,
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


class DegradedError(BaseServiceError):
    """Fallback 사용 가능한 성능 저하 오류."""

    def __init__(
        self,
        message: str,
        service: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.DEGRADED,
            service=service,
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


# Service-specific errors

class LLMError(TransientError):
    """LLM 서비스 오류 (일시적, 재시도 가능)."""

    def __init__(
        self,
        message: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            service="llm",
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


class EmbeddingError(PermanentError):
    """Embedding 서비스 오류 (영구적)."""

    def __init__(
        self,
        message: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            service="embedding",
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


class ChromaDBError(TransientError):
    """ChromaDB 서비스 오류 (일시적, 재시도 가능)."""

    def __init__(
        self,
        message: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            service="chromadb",
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )


class OpenAIError(TransientError):
    """OpenAI API 오류 (일시적, 재시도 가능)."""

    def __init__(
        self,
        message: str,
        operation: str,
        topic_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            service="openai",
            operation=operation,
            topic_id=topic_id,
            details=details,
            original_error=original_error,
        )
