"""Reference document models."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ReferenceSourceType(str, Enum):
    """Reference source types."""
    PDF_BOOK = "pdf_book"
    MARKDOWN = "markdown"
    # BLOG source type removed - deferred to future enhancement
    # TODO: Implement blog parser for https://blog.skby.net with:
    #   - BeautifulSoup4 HTML parsing
    #   - URL management (deduplication, content_hash comparison)
    #   - robots.txt compliance
    #   - Rate limiting (1 second interval)


class ReferenceDocument(BaseModel):
    """참조 문서."""
    id: str
    source_type: ReferenceSourceType
    title: str
    content: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    domain: str
    embedding: Optional[List[float]] = None
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    last_updated: datetime

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReferenceCreate(BaseModel):
    """참조 문서 생성."""
    source_type: ReferenceSourceType
    title: str
    content: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    domain: str
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0)


class MatchedReference(BaseModel):
    """매칭된 참조 문서."""
    reference_id: str
    title: str
    source_type: ReferenceSourceType
    similarity_score: float
    domain: str
    trust_score: float
    relevant_snippet: str

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReferenceIndexRequest(BaseModel):
    """참조 문서 인덱싱 요청."""
    source_paths: List[str] = Field(description="파일 경로 또는 URL 목록")
    source_type: ReferenceSourceType
    domain: Optional[str] = None
    force_reindex: bool = Field(default=False, description="기존 인덱스 덮어쓰기")


class ReferenceIndexResponse(BaseModel):
    """인덱싱 응답."""
    indexed_count: int
    failed_count: int
    failed_paths: List[str]
    duration_seconds: float
