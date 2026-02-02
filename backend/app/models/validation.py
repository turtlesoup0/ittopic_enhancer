"""Validation models."""
from pydantic import BaseModel, Field
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

# Forward reference to avoid circular import
if TYPE_CHECKING:
    from app.models.reference import MatchedReference
else:
    # Runtime import - MatchedReference is needed before ValidationResult
    from app.models.reference import MatchedReference


class GapType(str, Enum):
    """Content gap types."""
    MISSING_FIELD = "missing_field"
    INCOMPLETE_DEFINITION = "incomplete_definition"
    MISSING_KEYWORDS = "missing_keywords"
    OUTDATED_CONTENT = "outdated_content"
    INACCURATE_INFO = "inaccurate_info"
    INSUFFICIENT_DEPTH = "insufficient_depth"
    MISSING_EXAMPLE = "missing_example"
    INCONSISTENT_CONTENT = "inconsistent_content"


class ContentGap(BaseModel):
    """콘텐츠 격차."""
    gap_type: GapType
    field_name: str
    current_value: str
    suggested_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    reference_id: str
    reasoning: str = ""

    # Priority calculation fields
    missing_count: int = Field(default=1, ge=0, description="누락된 항목 수 (키워드 등)")
    required_count: int = Field(default=1, ge=1, description="필수 항목 수")
    gap_details: dict = Field(default_factory=dict, description="추가 gap 상세 정보")


class ValidationResult(BaseModel):
    """검증 결과."""
    id: str
    topic_id: str
    overall_score: float = Field(ge=0.0, le=1.0, description="0.0 - 1.0 전체 점수")
    gaps: List[ContentGap] = Field(default_factory=list)
    matched_references: List[MatchedReference] = Field(default_factory=list)
    validation_timestamp: datetime = Field(default_factory=datetime.now)

    # Detailed scores
    field_completeness_score: float = Field(ge=0.0, le=1.0)
    content_accuracy_score: float = Field(ge=0.0, le=1.0)
    reference_coverage_score: float = Field(ge=0.0, le=1.0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ValidationRequest(BaseModel):
    """검증 요청."""
    topic_ids: List[str] = Field(max_length=100)
    domain_filter: Optional[str] = None
    reference_domains: List[str] = Field(default_factory=lambda: ["all"])


class ValidationResponse(BaseModel):
    """검증 응답 (async task)."""
    task_id: str
    status: str
    estimated_time: int = Field(description="예상 소요 시간 (초)")


class ValidationTaskStatus(BaseModel):
    """검증 태스크 상태."""
    task_id: str
    status: str  # queued, processing, completed, failed
    progress: int = Field(ge=0, le=100, default=0)
    total: int = 1
    current: int = 0
    error: Optional[str] = None
    results: Optional[List[ValidationResult]] = None
