"""표준 API 응답 모델."""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import uuid4

from app.core.errors import ErrorCode, ErrorResponse


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    표준 API 응답 포맷.

    모든 API 엔드포인트는 이 포맷을 사용하여 응답합니다.
    """

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )

    success: bool = Field(..., description="요청 성공 여부")
    data: Optional[T] = Field(None, description="응답 데이터")
    error: Optional[ErrorResponse] = Field(None, description="에러 정보 (실패 시)")
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="요청 추적 ID"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="응답 생성 시간"
    )

    @classmethod
    def success_response(
        cls,
        data: T,
        request_id: Optional[str] = None,
    ) -> "ApiResponse[T]":
        """
        성공 응답 생성.

        Args:
            data: 응답 데이터
            request_id: 요청 ID (없으면 자동 생성)

        Returns:
            ApiResponse 인스턴스
        """
        return cls(
            success=True,
            data=data,
            request_id=request_id or str(uuid4()),
        )

    @classmethod
    def error_response(
        cls,
        code: ErrorCode,
        message: str,
        details: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> "ApiResponse[None]":
        """
        에러 응답 생성.

        Args:
            code: 에러 코드
            message: 에러 메시지
            details: 추가 에러 상세 정보
            request_id: 요청 ID (없으면 자동 생성)

        Returns:
            ApiResponse 인스턴스
        """
        return cls(
            success=False,
            error=ErrorResponse(
                code=code,
                message=message,
                details=details or {},
            ),
            request_id=request_id or str(uuid4()),
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    페이지네이션 응답 모델.

    리스트 데이터와 페이지 정보를 함께 반환합니다.
    """

    items: list[T] = Field(..., description="데이터 목록")
    total: int = Field(..., description="전체 데이터 개수")
    page: int = Field(..., description="현재 페이지 번호 (1부터 시작)")
    size: int = Field(..., description="페이지당 데이터 개수")
    total_pages: int = Field(..., description="전체 페이지 수")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        size: int,
    ) -> "PaginatedResponse[T]":
        """
        페이지네이션 응답 생성.

        Args:
            items: 데이터 목록
            total: 전체 데이터 개수
            page: 현재 페이지 번호
            size: 페이지당 데이터 개수

        Returns:
            PaginatedResponse 인스턴스
        """
        total_pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
