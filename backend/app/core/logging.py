"""Structured logging configuration."""
import structlog
from typing import Any, Optional
from app.core.errors import BaseServiceError


def configure_logging(settings: Any) -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a structured logger."""
    return structlog.get_logger(name)


def log_error(
    logger: structlog.BoundLogger,
    error: BaseServiceError,
    additional_context: Optional[dict[str, Any]] = None,
) -> None:
    """
    구조화된 에러 로그 기록.

    Args:
        logger: Structured logger 인스턴스
        error: BaseServiceError 인스턴스
        additional_context: 추가 컨텍스트 정보
    """
    error_dict = error.to_dict()
    if additional_context:
        error_dict.update(additional_context)

    # 에러 카테고리에 따른 로그 레벨 결정
    if error.category.value == "transient":
        logger.warning("error_transient", **error_dict)
    elif error.category.value == "permanent":
        logger.error("error_permanent", **error_dict)
    else:  # degraded
        logger.info("error_degraded", **error_dict)

    # 원본 에러가 있으면 스택 트레이스 로그
    if error.original_error:
        logger.exception(
            "error_original_exception",
            error_type=type(error.original_error).__name__,
            **error_dict,
        )


def log_service_error(
    logger: structlog.BoundLogger,
    service: str,
    operation: str,
    message: str,
    topic_id: Optional[str] = None,
    additional_context: Optional[dict[str, Any]] = None,
) -> None:
    """
    서비스 오류 로그 기록 (간소화된 버전).

    Args:
        logger: Structured logger 인스턴스
        service: 서비스 이름
        operation: 수행 중인 작업
        message: 에러 메시지
        topic_id: 토픽 ID
        additional_context: 추가 컨텍스트
    """
    log_data = {
        "service": service,
        "operation": operation,
        "topic_id": topic_id,
    }
    if additional_context:
        log_data.update(additional_context)

    logger.error("service_error", msg=message, **log_data)
