"""Error categories and exception hierarchy for resilience."""
from typing import Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """표준 API 에러 코드."""

    # Validation errors (1xx)
    VALIDATION_ERROR = "VALIDATION_001"
    INVALID_INPUT = "VALIDATION_002"
    MISSING_REQUIRED_FIELD = "VALIDATION_003"

    # Not found errors (2xx)
    NOT_FOUND = "NOT_FOUND_002"
    RESOURCE_NOT_FOUND = "NOT_FOUND_003"

    # Authentication errors (3xx)
    AUTH_FAILED = "AUTH_003"
    UNAUTHORIZED = "AUTH_004"
    INVALID_API_KEY = "AUTH_005"

    # Rate limiting errors (4xx)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_004"

    # Internal errors (5xx)
    INTERNAL_ERROR = "INTERNAL_005"
    DATABASE_ERROR = "INTERNAL_006"
    SERVICE_UNAVAILABLE = "INTERNAL_007"


class ErrorResponse(BaseModel):
    """표준 에러 응답 모델."""

    code: ErrorCode = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: dict[str, Any] = Field(default_factory=dict, description="추가 에러 상세 정보")


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
