"""Enhancement proposal models."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ProposalPriority(str, Enum):
    """보강 제안 우선순위."""
    CRITICAL = "critical"  # 시험 필수 내용 누락
    HIGH = "high"         # 중요 개선 필요
    MEDIUM = "medium"     # 보강 권장
    LOW = "low"           # 선택적 개선


class EnhancementProposal(BaseModel):
    """보강 제안."""
    id: str
    topic_id: str
    priority: ProposalPriority
    title: str
    description: str
    current_content: str
    suggested_content: str
    reasoning: str
    reference_sources: List[str] = Field(default_factory=list)
    estimated_effort: int = Field(description="예상 소요 시간 (분)", ge=1, le=120)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    applied: bool = Field(default=False)
    rejected: bool = Field(default=False)


class ProposalListResponse(BaseModel):
    """제안 목록 응답."""
    proposals: List[EnhancementProposal]
    total: int
    topic_id: str


class ProposalApplyRequest(BaseModel):
    """제안 적용 요청."""
    proposal_id: str
    topic_id: str


class ProposalApplyResponse(BaseModel):
    """제안 적용 응답."""
    success: bool
    message: str
    updated_content: Optional[str] = None
