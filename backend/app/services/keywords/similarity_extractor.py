"""의미적 키워드 추천 서비스.

주제 수준의 의미 유사성을 기반으로 키워드를 추천하는 서비스입니다.
도메인 수준 접근 방식의 문제점을 해결하기 위해, 각 주제의 콘텐츠를
분석하여 의미적으로 관련된 키워드를 추천합니다.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.models.topic import Topic
from app.services.matching.embedding import EmbeddingService, get_embedding_service
from app.services.matching.keyword_extractor import KeywordExtractor

logger = logging.getLogger(__name__)


class KeywordMatch:
    """키워드 매칭 결과."""

    def __init__(
        self,
        keyword: str,
        similarity: float,
        source: str,
    ):
        """키워드 매칭 결과를 생성합니다.

        Args:
            keyword: 키워드
            similarity: 유사성 점수 (0.0 ~ 1.0)
            source: 출처 문서
        """
        self.keyword = keyword
        self.similarity = similarity
        self.source = source

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환합니다."""
        return {
            "keyword": self.keyword,
            "similarity": self.similarity,
            "source": self.source,
        }


class KeywordEmbeddingRepository:
    """키워드 임베딩 저장소.

    참조 문서에서 추출한 키워드와 임베딩을 저장하고,
    주제와 의미적으로 유사한 키워드를 검색합니다.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
    ):
        """저장소를 초기화합니다.

        Args:
            embedding_service: 임베딩 서비스 (기본값: 전역 인스턴스)
        """
        self._embedding_service = embedding_service or get_embedding_service()
        self._keywords: dict[str, np.ndarray] = {}
        self._sources: dict[str, str] = {}

    @property
    def size(self) -> int:
        """저장된 키워드 수를 반환합니다."""
        return len(self._keywords)

    async def add_keyword(
        self,
        keyword: str,
        embedding: np.ndarray,
        source: str,
    ) -> None:
        """키워드 임베딩을 추가합니다.

        Args:
            keyword: 키워드
            embedding: 임베딩 벡터
            source: 출처 문서
        """
        self._keywords[keyword] = embedding
        self._sources[keyword] = source
        logger.debug(f"Added keyword: {keyword} from {source}")

    async def add_keywords_batch(
        self,
        keywords: list[str],
        embeddings: list[np.ndarray],
        source: str,
    ) -> None:
        """여러 키워드 임베딩을 일괄 추가합니다.

        Args:
            keywords: 키워드 목록
            embeddings: 임베딩 벡터 목록
            source: 출처 문서
        """
        for keyword, embedding in zip(keywords, embeddings):
            await self.add_keyword(keyword, embedding, source)

    async def find_similar(
        self,
        topic_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.7,
    ) -> list[KeywordMatch]:
        """유사한 키워드를 검색합니다.

        Args:
            topic_embedding: 주제 임베딩
            top_k: 반환할 상위 K개 결과
            threshold: 유사성 임계값

        Returns:
            유사한 키워드 목록 (유사성 내림차순)
        """
        if not self._keywords:
            logger.warning("No keywords indexed in repository")
            return []

        similarities = []

        for keyword, embedding in self._keywords.items():
            # 코사인 유사성 계산
            similarity = self._embedding_service.compute_similarity(topic_embedding, embedding)

            # 임계값 필터링
            if similarity >= threshold:
                similarities.append(
                    KeywordMatch(
                        keyword=keyword,
                        similarity=similarity,
                        source=self._sources[keyword],
                    )
                )

        # 유사성 내림차순 정렬
        similarities.sort(key=lambda x: x.similarity, reverse=True)

        # 상위 K개 반환
        return similarities[:top_k]

    def clear(self) -> None:
        """모든 키워드를 제거합니다."""
        self._keywords.clear()
        self._sources.clear()
        logger.info("Cleared keyword repository")


class SemanticKeywordService:
    """의미적 키워드 추천 서비스.

    주제 콘텐츠를 기반으로 의미적으로 관련된 키워드를 추천합니다.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        data_sources: dict[str, str] | None = None,
    ):
        """서비스를 초기화합니다.

        Args:
            embedding_service: 임베딩 서비스 (기본값: 전역 인스턴스)
            data_sources: 데이터 소스 경로 매핑
        """
        self._embedding_service = embedding_service or get_embedding_service()
        self._extractor = KeywordExtractor(use_synonyms=True, use_stopwords=True)
        self._repo = KeywordEmbeddingRepository(self._embedding_service)
        self._initialized = False

        # 기본 데이터 소스 경로
        if data_sources is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_sources = {
                "600제": str(project_root / "data" / "600제_분리_v5_rounds"),
                "서브노트": str(project_root / "data" / "서브노트_통합"),
            }
        self._data_sources = data_sources

    @property
    def repository(self) -> KeywordEmbeddingRepository:
        """키워드 저장소를 반환합니다."""
        return self._repo

    @property
    def is_initialized(self) -> bool:
        """초기화 완료 여부를 반환합니다."""
        return self._initialized

    def _prepare_topic_text(self, topic: Topic) -> str:
        """임베딩을 위한 주제 텍스트를 준비합니다.

        Args:
            topic: 주제 모델

        Returns:
            임베딩용 텍스트
        """
        parts = []

        # 정의 (가장 중요)
        if topic.content.정의:
            parts.append(topic.content.정의)

        # 리드문
        if topic.content.리드문:
            parts.append(topic.content.리드문)

        # 기존 키워드
        if topic.content.키워드:
            parts.append(" ".join(topic.content.키워드))

        return " ".join(parts)

    async def get_topic_embedding(self, topic: Topic) -> np.ndarray:
        """주제 임베딩을 생성합니다.

        Args:
            topic: 주제 모델

        Returns:
            주제 임베딩 벡터
        """
        text = self._prepare_topic_text(topic)

        if not text:
            logger.warning(f"Topic {topic.id} has no content for embedding")
            # 빈 텍스트는 기본 임베딩 반환
            text = "주제"

        return await self._embedding_service.encode_async(text)

    async def initialize_from_references(
        self,
        max_keywords_per_source: int = 100,
    ) -> None:
        """참조 문서에서 키워드를 추출하고 인덱싱합니다.

        Args:
            max_keywords_per_source: 각 문서에서 추출할 최대 키워드 수
        """
        if self._initialized:
            logger.info("SemanticKeywordService already initialized")
            return

        logger.info("Initializing SemanticKeywordService from reference documents...")

        total_keywords = 0

        for source_name, source_path in self._data_sources.items():
            source_dir = Path(source_path)

            if not source_dir.exists():
                logger.warning(f"Data source not found: {source_path}")
                continue

            # 디렉토리인 경우 하위 파일 처리
            if source_dir.is_dir():
                keywords_added = await self._index_directory(
                    source_dir, source_name, max_keywords_per_source
                )
                total_keywords += keywords_added

        self._initialized = True
        logger.info(f"SemanticKeywordService initialized: {total_keywords} keywords indexed")

    async def _index_directory(
        self,
        directory: Path,
        source_name: str,
        max_keywords: int,
    ) -> int:
        """디렉토리의 모든 파일에서 키워드를 인덱싱합니다.

        Args:
            directory: 디렉토리 경로
            source_name: 소스 이름
            max_keywords: 최대 키워드 수

        Returns:
            추가된 키워드 수
        """
        keywords_added = 0

        for md_file in directory.rglob("*.md"):
            try:
                with open(md_file, encoding="utf-8") as f:
                    content = f.read()

                # YAML frontmatter 제거
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2]

                # 키워드 추출
                keywords = self._extractor.extract_keywords(content, top_k=max_keywords)

                if not keywords:
                    continue

                # 키워드 임베딩 생성
                embeddings = await self._embedding_service.encode_async(keywords)

                # 배치 추가
                source_id = f"{source_name}_{md_file.stem}"
                if isinstance(embeddings, np.ndarray):
                    if embeddings.ndim == 1:
                        embeddings = [embeddings]
                    else:
                        embeddings = list(embeddings)
                else:
                    embeddings = list(embeddings)

                await self._repo.add_keywords_batch(keywords, embeddings, source_id)
                keywords_added += len(keywords)

            except Exception as e:
                logger.warning(f"Failed to index {md_file}: {e}")
                continue

        return keywords_added

    async def suggest_keywords_by_topic(
        self,
        topic: Topic,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> list[dict[str, Any]]:
        """주제 기반 키워드를 추천합니다.

        Args:
            topic: 주제 모델
            top_k: 반환할 상위 K개 키워드
            similarity_threshold: 유사성 임계값

        Returns:
            추천 키워드 목록
        """
        if not self._initialized:
            logger.warning("Service not initialized, initializing now...")
            await self.initialize_from_references()

        # 주제 임베딩 생성
        topic_embedding = await self.get_topic_embedding(topic)

        # 유사한 키워드 검색
        matches = await self._repo.find_similar(
            topic_embedding,
            top_k=top_k,
            threshold=similarity_threshold,
        )

        # 결과 변환
        return [match.to_dict() for match in matches]


# 전역 서비스 인스턴스
_semantic_service: SemanticKeywordService | None = None


async def get_semantic_service() -> SemanticKeywordService:
    """전역 의미적 키워드 서비스 인스턴스를 반환합니다.

    Returns:
        SemanticKeywordService 인스턴스
    """
    global _semantic_service

    if _semantic_service is None:
        _semantic_service = SemanticKeywordService()
        await _semantic_service.initialize_from_references()

    return _semantic_service
