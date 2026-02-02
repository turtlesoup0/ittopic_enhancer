"""Resilience patterns: Circuit Breaker and Retry decorators."""
import asyncio
import time
from typing import Any, Callable, Optional, TypeVar
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.errors import BaseServiceError, ErrorCategory, TransientError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """
    Circuit Breaker 패턴 구현.

    States:
    - CLOSED: 정상 작동, 요청 통과
    - OPEN: 장애 감지, 요청 차단 (failure_threshold 초과)
    - HALF_OPEN: 복구 시도, 일부 요청 통과 (timeout 후)
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Circuit Breaker 초기화.

        Args:
            service_name: 서비스 이름 (로깅용)
            failure_threshold: 회로 차단 실패 횟수
            recovery_timeout: 복구 대기 시간 (초)
            expected_exception: 회로 차단을 트리거할 예외 타입
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        """현재 회로 상태."""
        # OPEN 상태에서 recovery_timeout 경과 시 HALF_OPEN으로 전환
        if self._state == "OPEN":
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                logger.info(
                    "circuit_breaker_state_changed",
                    service=self.service_name,
                    from_state="OPEN",
                    to_state="HALF_OPEN",
                )
        return self._state

    def _record_success(self):
        """성공 기록."""
        with self._lock:
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
                self._failure_count = 0
                logger.info(
                    "circuit_breaker_recovered",
                    service=self.service_name,
                    state="CLOSED",
                )
            elif self._state == "CLOSED":
                self._failure_count = 0

    def _record_failure(self):
        """실패 기록."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                old_state = self._state
                self._state = "OPEN"
                logger.warning(
                    "circuit_breaker_opened",
                    service=self.service_name,
                    from_state=old_state,
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                )

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Circuit Breaker를 통한 함수 실행.

        Args:
            func: 실행할 함수
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            TransientError: 회로가 OPEN 상태인 경우
        """
        current_state = self.state

        if current_state == "OPEN":
            logger.warning(
                "circuit_breaker_rejected",
                service=self.service_name,
                state="OPEN",
                operation=func.__name__,
            )
            raise TransientError(
                message=f"Circuit breaker is OPEN for {self.service_name}",
                service=self.service_name,
                operation=func.__name__,
            )

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            raise


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    topic_id_param: str = "topic_id",
):
    """
    지수 백오프를 사용하는 재시도 데코레이터.

    Args:
        max_attempts: 최대 시도 횟수
        wait_min: 최소 대기 시간 (초)
        wait_max: 최대 대기 시간 (초)
        topic_id_param: topic_id 파라미터 이름 (로깅용)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract topic_id from kwargs for logging
            topic_id = kwargs.get(topic_id_param)

            async def _retry_logic() -> T:
                return await func(*args, **kwargs)

            # Configure tenacity retry
            retryer = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(TransientError),
                before_sleep=before_sleep_log(logger, "WARNING"),
                reraise=True,
            )

            # Apply retry wrapper
            retried_func = retryer(_retry_logic)

            try:
                return await retried_func()
            except Exception as e:
                logger.error(
                    "retry_failed",
                    function=func.__name__,
                    topic_id=topic_id,
                    attempts=max_attempts,
                    error=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract topic_id from kwargs for logging
            topic_id = kwargs.get(topic_id_param)

            # Configure tenacity retry
            retryer = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(TransientError),
                before_sleep=before_sleep_log(logger, "WARNING"),
                reraise=True,
            )

            # Apply retry wrapper
            retried_func = retryer(func)

            try:
                return retried_func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "retry_failed",
                    function=func.__name__,
                    topic_id=topic_id,
                    attempts=max_attempts,
                    error=str(e),
                )
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# Global Circuit Breaker instances

_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    """
    서비스용 Circuit Breaker 인스턴스 가져오기.

    Args:
        service_name: 서비스 이름
        failure_threshold: 회로 차단 실패 횟수
        recovery_timeout: 복구 대기 시간 (초)

    Returns:
        CircuitBreaker 인스턴스
    """
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _circuit_breakers[service_name]


async def with_circuit_breaker(
    service_name: str,
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Circuit Breaker와 함께 함수 실행.

    Args:
        service_name: 서비스 이름
        func: 실행할 함수
        *args: 위치 인자
        **kwargs: 키워드 인자

    Returns:
        함수 실행 결과
    """
    cb = get_circuit_breaker(service_name)
    return await cb.call(func, *args, **kwargs)
