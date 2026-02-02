"""Topic models for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DomainEnum(str, Enum):
    """Supported domains."""
    신기술 = "신기술"
    정보보안 = "정보보안"
    네트워크 = "네트워크"
    데이터베이스 = "데이터베이스"
    SW = "SW"
    프로젝트관리 = "프로젝트관리"


class ExamFrequencyEnum(str, Enum):
    """Exam frequency levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TopicMetadata(BaseModel):
    """토픽 메타데이터."""
    file_path: str
    file_name: str
    folder: str
    domain: DomainEnum
    exam_frequency: ExamFrequencyEnum = ExamFrequencyEnum.MEDIUM


class TopicContent(BaseModel):
    """토픽 내용."""
    리드문: str = Field(default="")
    정의: str = Field(default="")
    키워드: List[str] = Field(default_factory=list)
    해시태그: str = Field(default="")
    암기: str = Field(default="")


class TopicCompletionStatus(BaseModel):
    """필드 완성도."""
    리드문: bool = False
    정의: bool = False
    키워드: bool = False
    해시태그: bool = False
    암기: bool = False


class Topic(BaseModel):
    """전체 토픽 모델."""
    id: str
    metadata: TopicMetadata
    content: TopicContent
    completion: TopicCompletionStatus
    embedding: Optional[List[float]] = None
    last_validated: Optional[datetime] = None
    validation_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TopicCreate(BaseModel):
    """토픽 생성 요청."""
    file_path: str
    file_name: str
    folder: str
    domain: DomainEnum
    exam_frequency: ExamFrequencyEnum = ExamFrequencyEnum.MEDIUM
    리드문: str = ""
    정의: str = ""
    키워드: List[str] = Field(default_factory=list)
    해시태그: str = ""
    암기: str = ""


class TopicUpdate(BaseModel):
    """토픽 업데이트 요청."""
    리드문: Optional[str] = None
    정의: Optional[str] = None
    키워드: Optional[List[str]] = None
    해시태그: Optional[str] = None
    암기: Optional[str] = None


class TopicListResponse(BaseModel):
    """토픽 목록 응답."""
    topics: List[Topic]
    total: int
    page: int
    size: int
