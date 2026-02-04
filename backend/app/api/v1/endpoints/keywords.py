"""Keywords API endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_request_id, get_db
from app.core.api import ApiResponse
from app.core.logging import get_logger
from app.db.repositories.topic import TopicRepository
from app.services.keywords import get_semantic_service
from app.services.matching.keyword_extractor import KeywordExtractor

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models for Semantic Keyword Suggestion
# =============================================================================


class KeywordByTopicRequest(BaseModel):
    """주제 기반 키워드 추천 요청."""

    topic_id: str = Field(..., description="주제 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="반환할 키워드 수")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="유사성 임계값")


class KeywordSuggestion(BaseModel):
    """키워드 추천 결과."""

    keyword: str = Field(..., description="키워드")
    similarity: float = Field(..., description="유사성 점수")
    source: str = Field(..., description="출처 문서")


# 데이터 소스 경로 설정
DATA_SOURCES = {
    "600제": "/Users/turtlesoup0-macmini/Documents/itpe-topic-enhancement/data/600제_분리_v5_rounds/",
    "서브노트": "/Users/turtlesoup0-macmini/Documents/itpe-topic-enhancement/data/서브노트_통합/",
}

# 도메인별 서브노트 디렉토리 매핑
DOMAIN_SUBNOTE_MAPPING = {
    "SW": "SW",
    "NW": "NW",
    "DB": "DB",
    "정보보안": "정보보안",
    "신기술": "신기술",
    "경영": "경영",
    "기타": "기타",
}


class KeywordSuggestionService:
    """키워드 추천 서비스."""

    def __init__(self):
        """서비스 초기화."""
        self.extractor = KeywordExtractor(use_synonyms=True, use_stopwords=True)
        self.base_data_path = Path(
            "/Users/turtlesoup0-macmini/Documents/itpe-topic-enhancement/data"
        )

    def _collect_text_from_domain(self, domain: str | None) -> str:
        """
        도메인별 데이터 소스에서 텍스트를 수집합니다.

        Args:
            domain: 필터링할 도메인 (None인 경우 모든 도메인)

        Returns:
            수집된 텍스트
        """
        all_text = []

        # 서브노트에서 텍스트 수집
        subnote_path = self.base_data_path / "서브노트_통합"
        if subnote_path.exists():
            if domain:
                # 특정 도메인만 수집
                domain_dir = subnote_path / domain
                if domain_dir.exists():
                    all_text.extend(self._collect_markdown_files(domain_dir))
            else:
                # 모든 도메인 수집
                for domain_dir in subnote_path.iterdir():
                    if domain_dir.is_dir():
                        all_text.extend(self._collect_markdown_files(domain_dir))

        # 600제에서 텍스트 수집 (도메인 필터 없이 전체)
        ce_600_path = self.base_data_path / "600제_분리_v5_rounds"
        if ce_600_path.exists():
            # SW 도메인만 수집 (600제는 주로 SW 관련)
            if not domain or domain == "SW":
                all_text.extend(self._collect_markdown_files(ce_600_path))

        return "\n".join(all_text)

    def _collect_markdown_files(self, directory: Path) -> list[str]:
        """
        디렉토리의 모든 Markdown 파일에서 텍스트를 추출합니다.

        Args:
            directory: 검색할 디렉토리

        Returns:
            추출된 텍스트 목록
        """
        texts = []

        for md_file in directory.rglob("*.md"):
            try:
                with open(md_file, encoding="utf-8") as f:
                    content = f.read()
                    # YAML frontmatter 제거
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            content = parts[2]
                    texts.append(content)
            except Exception as e:
                logger.warning(f"Failed to read {md_file}: {e}")
                continue

        return texts

    def suggest_keywords(
        self,
        domain: str | None = None,
        top_k: int = 10,
    ) -> list[str]:
        """
        데이터 소스에서 키워드를 추출하여 추천합니다.

        Args:
            domain: 필터링할 도메인
            top_k: 반환할 키워드 수

        Returns:
            추천 키워드 목록 (빈도수 내림차순)
        """
        # 텍스트 수집
        text = self._collect_text_from_domain(domain)

        if not text:
            logger.warning(f"No text found for domain: {domain}")
            return []

        # 키워드 추출
        keywords = self.extractor.extract_keywords(text, top_k=top_k)

        return keywords


# 전역 서비스 인스턴스
_keyword_service: KeywordSuggestionService | None = None


def get_keyword_service() -> KeywordSuggestionService:
    """키워드 서비스 인스턴스를 반환합니다."""
    global _keyword_service
    if _keyword_service is None:
        _keyword_service = KeywordSuggestionService()
    return _keyword_service


@router.get("/suggest", response_model=ApiResponse)
async def suggest_keywords(
    domain: str | None = Query(
        None, description="필터링할 도메인 (SW, NW, DB, 정보보안, 신기술, 경영, 기타)"
    ),
    top_k: int = Query(10, ge=1, le=50, description="반환할 키워드 수"),
    request_id: str = Depends(get_current_request_id),
):
    """
    데이터 소스에서 키워드를 추출하여 추천합니다.

    ## Parameters
    - **domain**: (선택) 필터링할 도메인 (SW, NW, DB, 정보보안, 신기술, 경영, 기타)
    - **top_k**: 반환할 키워드 수 (기본값: 10, 최대: 50)

    ## Returns
    - **keywords**: 추천 키워드 목록 (빈도수 내림차순)

    ## Examples
    - 모든 도메인: `GET /api/v1/keywords/suggest`
    - SW 도메인: `GET /api/v1/keywords/suggest?domain=SW`
    - 20개 키워드: `GET /api/v1/keywords/suggest?top_k=20`
    """
    try:
        service = get_keyword_service()
        keywords = service.suggest_keywords(domain=domain, top_k=top_k)

        if not keywords:
            return ApiResponse.error_response(
                message="데이터 소스를 찾을 수 없거나 키워드를 추출할 수 없습니다.",
                details={"domain": domain, "top_k": top_k},
                request_id=request_id,
            )

        return ApiResponse.success_response(
            data={"keywords": keywords, "count": len(keywords)},
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to suggest keywords: {e}")
        return ApiResponse.error_response(
            message="키워드 추출 중 오류가 발생했습니다.",
            details={"error": str(e)},
            request_id=request_id,
        )


@router.post("/suggest-by-topic", response_model=ApiResponse)
async def suggest_keywords_by_topic(
    request: KeywordByTopicRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_current_request_id),
):
    """
    주제 기반 의미적 키워드 추천 API.

    주제의 콘텐츠(정의, 리드문, 키워드)를 분석하여
    의미적으로 관련된 키워드를 추천합니다.

    ## Parameters
    - **topic_id**: 주제 ID (필수)
    - **top_k**: 반환할 키워드 수 (기본값: 5, 범위: 1-20)
    - **similarity_threshold**: 유사성 임계값 (기본값: 0.7, 범위: 0.0-1.0)

    ## Returns
    - **keywords**: 추천 키워드 목록 (유사성 내림차순)
    - **count**: 반환된 키워드 수

    ## Example Request
    ```json
    {
      "topic_id": "abc-123",
      "top_k": 5,
      "similarity_threshold": 0.7
    }
    ```

    ## Example Response
    ```json
    {
      "success": true,
      "data": {
        "keywords": [
          {"keyword": "캡슐화", "similarity": 0.92, "source": "600제_SW_120회"},
          {"keyword": "상속", "similarity": 0.89, "source": "서브노트_SW_OOP"}
        ],
        "count": 2
      }
    }
    ```
    """
    try:
        # 주제 조회
        topic_repo = TopicRepository(db)
        topic = await topic_repo.get_by_id(request.topic_id)

        if not topic:
            return ApiResponse.error_response(
                message="주제를 찾을 수 없습니다.",
                details={"topic_id": request.topic_id},
                request_id=request_id,
            )

        # 의미적 키워드 추천 서비스
        semantic_service = await get_semantic_service()

        # 키워드 추천
        suggestions = await semantic_service.suggest_keywords_by_topic(
            topic=topic,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        return ApiResponse.success_response(
            data={
                "topic_id": topic.id,
                "keywords": suggestions,
                "count": len(suggestions),
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to suggest keywords by topic: {e}")
        return ApiResponse.error_response(
            message="주제 기반 키워드 추천 중 오류가 발생했습니다.",
            details={"error": str(e)},
            request_id=request_id,
        )
