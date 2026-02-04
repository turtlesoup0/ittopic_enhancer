"""API 미들웨어."""
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Request ID 추적 미들웨어.

    모든 요청에 고유 ID를 부여하고 로깅 및 응답에 포함합니다.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
    ) -> None:
        """
        미들웨어 초기화.

        Args:
            app: ASGI 애플리케이션
            header_name: Request ID 헤더 이름
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        요청 처리 및 Request ID 부여.

        Args:
            request: FastAPI 요청 객체
            call_next: 다음 미들웨어/라우터 호출

        Returns:
            응답 객체에 Request ID 헤더가 포함됨
        """
        # 기존 Request ID 확인 (헤더에서)
        request_id = request.headers.get(self.header_name)

        # 없으면 새로 생성
        if not request_id:
            request_id = str(uuid4())

        # 요청 상태에 Request ID 저장 (다른 미들웨어/라우터에서 접근 가능)
        request.state.request_id = request_id

        # 로거에 Request ID 컨텍스트 추가 (다른 변수명 사용)
        request_logger = logger.bind(request_id=request_id)

        # 요청 로깅
        request_logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # 다음 미들웨어/라우터 호출
        try:
            response = await call_next(request)

            # 응답에 Request ID 헤더 추가
            response.headers[self.header_name] = request_id

            # 응답 로깅
            request_logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )

            return response

        except Exception as e:
            # 에러 로깅 (모듈 레벨 logger 사용)
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


async def get_request_id(request: Request) -> str:
    """
    요청에서 Request ID 추출.

    Args:
        request: FastAPI 요청 객체

    Returns:
        Request ID 문자열
    """
    # state에 저장된 Request ID 반환
    if hasattr(request.state, "request_id"):
        return request.state.request_id

    # 없으면 새로 생성
    return str(uuid4())
