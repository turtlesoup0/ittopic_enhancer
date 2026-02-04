"""Unit tests for SemanticKeywordService module.

Tests for the topic-level semantic similarity keyword extraction service.
"""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from app.models.topic import (
    DomainEnum,
    Topic,
    TopicCompletionStatus,
    TopicContent,
    TopicMetadata,
)
from app.services.keywords.similarity_extractor import (
    KeywordEmbeddingRepository,
    KeywordMatch,
    SemanticKeywordService,
)


class TestKeywordMatch:
    """KeywordMatch 테스트."""

    def test_keyword_match_creation(self):
        """KeywordMatch 생성 테스트."""
        match = KeywordMatch(
            keyword="캡슐화",
            similarity=0.92,
            source="600제_SW_120회",
        )

        assert match.keyword == "캡슐화"
        assert match.similarity == 0.92
        assert match.source == "600제_SW_120회"

    def test_to_dict(self):
        """to_dict 메서드 테스트."""
        match = KeywordMatch(
            keyword="상속",
            similarity=0.89,
            source="서브노트_SW_OOP",
        )

        result = match.to_dict()

        assert result == {
            "keyword": "상속",
            "similarity": 0.89,
            "source": "서브노트_SW_OOP",
        }


class TestKeywordEmbeddingRepository:
    """KeywordEmbeddingRepository 테스트."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock()
        service.compute_similarity = Mock(return_value=0.8)
        return service

    @pytest.fixture
    def repository(self, mock_embedding_service):
        """KeywordEmbeddingRepository fixture."""
        return KeywordEmbeddingRepository(embedding_service=mock_embedding_service)

    @pytest.mark.asyncio
    async def test_add_keyword(self, repository):
        """키워드 추가 테스트."""
        embedding = np.array([0.1] * 768)

        await repository.add_keyword("캡슐화", embedding, "600제_SW")

        assert repository.size == 1
        assert "캡슐화" in repository._keywords
        assert repository._sources["캡슐화"] == "600제_SW"

    @pytest.mark.asyncio
    async def test_add_keywords_batch(self, repository):
        """일괄 키워드 추가 테스트."""
        keywords = ["캡슐화", "상속", "다형성"]
        embeddings = [np.array([0.1] * 768) for _ in keywords]

        await repository.add_keywords_batch(keywords, embeddings, "600제_SW")

        assert repository.size == 3

    @pytest.mark.asyncio
    async def test_find_similar_empty_repository(self, repository):
        """빈 저장소에서 검색 테스트."""
        topic_embedding = np.array([0.1] * 768)

        results = await repository.find_similar(topic_embedding)

        assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_with_threshold(self, repository, mock_embedding_service):
        """임계값 필터링 테스트."""
        # Add keywords
        await repository.add_keyword("캡슐화", np.array([0.1] * 768), "600제_SW")
        await repository.add_keyword("상속", np.array([0.2] * 768), "서브노트")

        topic_embedding = np.array([0.1] * 768)

        # Mock similarity values
        mock_embedding_service.compute_similarity.side_effect = [0.9, 0.5]

        results = await repository.find_similar(topic_embedding, threshold=0.7)

        # Only "캡슐화" should pass threshold
        assert len(results) == 1
        assert results[0].keyword == "캡슐화"

    @pytest.mark.asyncio
    async def test_find_similar_top_k(self, repository, mock_embedding_service):
        """상위 K개 결과 테스트."""
        # Add 5 keywords
        for i, keyword in enumerate(["캡슐화", "상속", "다형성", "추상화", "클래스"]):
            await repository.add_keyword(keyword, np.array([0.1] * 768), f"source_{i}")

        topic_embedding = np.array([0.1] * 768)

        # Mock similarity values (different for each)
        similarities = [0.9, 0.85, 0.8, 0.75, 0.7]
        mock_embedding_service.compute_similarity.side_effect = similarities

        results = await repository.find_similar(topic_embedding, top_k=3)

        # Should return top 3
        assert len(results) == 3
        # Should be sorted by similarity (descending)
        assert results[0].similarity == 0.9
        assert results[1].similarity == 0.85
        assert results[2].similarity == 0.8

    def test_clear(self, repository):
        """저장소 비우기 테스트."""
        repository._keywords = {"test": np.array([0.1] * 768)}
        repository._sources = {"test": "source"}

        repository.clear()

        assert repository.size == 0


class TestSemanticKeywordService:
    """SemanticKeywordService 테스트."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock()
        service.encode_async = AsyncMock(return_value=np.array([0.1] * 768))
        service.compute_similarity = Mock(return_value=0.8)
        return service

    @pytest.fixture
    def service(self, mock_embedding_service):
        """SemanticKeywordService fixture."""
        return SemanticKeywordService(
            embedding_service=mock_embedding_service,
            data_sources=None,  # Don't use real data sources in tests
        )

    @pytest.fixture
    def sample_topic(self):
        """Sample topic fixture."""
        return Topic(
            id="test-topic-1",
            metadata=TopicMetadata(
                file_path="/test/path.md",
                file_name="test.md",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="객체지향 프로그래밍의 핵심 개념",
                정의="캡슐화, 상속, 다형성을 지원하는 프로그래밍 패러다임",
                키워드=["OOP", "클래스", "객체"],
            ),
            completion=TopicCompletionStatus(),
        )

    def test_prepare_topic_text_with_all_fields(self, service, sample_topic):
        """모든 필드가 있는 경우 텍스트 준비 테스트."""
        text = service._prepare_topic_text(sample_topic)

        assert "캡슐화, 상속, 다형성을 지원하는 프로그래밍 패러다임" in text
        assert "객체지향 프로그래밍의 핵심 개념" in text
        assert "OOP" in text

    def test_prepare_topic_text_partial_fields(self, service):
        """일부 필드만 있는 경우 텍스트 준비 테스트."""
        topic = Topic(
            id="test-topic-2",
            metadata=TopicMetadata(
                file_path="/test/path2.md",
                file_name="test2.md",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="리드문만 있음",
                정의="",
                키워드=[],
            ),
            completion=TopicCompletionStatus(),
        )

        text = service._prepare_topic_text(topic)

        assert "리드문만 있음" in text
        assert len(text.strip()) > 0

    def test_prepare_topic_text_empty(self, service):
        """빈 주제 텍스트 준비 테스트."""
        topic = Topic(
            id="test-topic-3",
            metadata=TopicMetadata(
                file_path="/test/path3.md",
                file_name="test3.md",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="",
                정의="",
                키워드=[],
            ),
            completion=TopicCompletionStatus(),
        )

        text = service._prepare_topic_text(topic)

        # Empty text should return empty string or placeholder
        # Actual behavior: returns empty string
        assert text == ""

    @pytest.mark.asyncio
    async def test_get_topic_embedding(self, service, sample_topic, mock_embedding_service):
        """주제 임베딩 생성 테스트."""
        mock_embedding_service.encode_async = AsyncMock(return_value=np.array([0.5] * 768))

        embedding = await service.get_topic_embedding(sample_topic)

        # Check encode_async was called with prepared text
        mock_embedding_service.encode_async.assert_called_once()
        call_args = mock_embedding_service.encode_async.call_args[0][0]
        assert "캡슐화" in call_args or "리드문" in call_args

        # Check embedding is returned
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_suggest_keywords_by_topic_uninitialized(self, service, sample_topic):
        """초기화되지 않은 서비스 테스트."""
        # Mark as uninitialized
        service._initialized = False

        # Create a mock that simulates the side effect
        async def mock_init():
            service._initialized = True

        # Mock initialize to avoid file system access
        with patch.object(
            service, "initialize_from_references", new=AsyncMock(side_effect=mock_init)
        ):
            await service.suggest_keywords_by_topic(sample_topic)

        # Should have been called (check flag instead of mock)
        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_suggest_keywords_by_topic_with_results(
        self,
        service,
        sample_topic,
        mock_embedding_service,
    ):
        """키워드 추천 결과 반환 테스트."""
        # Mark as initialized to avoid auto-initialization
        service._initialized = True

        # Setup repository with keywords
        await service._repo.add_keyword("캡슐화", np.array([0.1] * 768), "600제_SW")
        await service._repo.add_keyword("상속", np.array([0.2] * 768), "서브노트")

        # Mock similarity
        mock_embedding_service.encode_async = AsyncMock(return_value=np.array([0.1] * 768))
        mock_embedding_service.compute_similarity.side_effect = [0.92, 0.89]

        results = await service.suggest_keywords_by_topic(
            sample_topic, top_k=5, similarity_threshold=0.7
        )

        assert len(results) == 2
        assert results[0]["keyword"] == "캡슐화"
        assert results[0]["similarity"] == 0.92
        assert results[0]["source"] == "600제_SW"

    @pytest.mark.asyncio
    async def test_suggest_keywords_by_topic_with_threshold_filtering(
        self,
        service,
        sample_topic,
        mock_embedding_service,
    ):
        """임계값 필터링 테스트."""
        service._initialized = True

        # Add keywords with varying similarities
        await service._repo.add_keyword("높은유사도", np.array([0.1] * 768), "source1")
        await service._repo.add_keyword("낮은유사도", np.array([0.2] * 768), "source2")

        mock_embedding_service.encode_async = AsyncMock(return_value=np.array([0.1] * 768))
        mock_embedding_service.compute_similarity.side_effect = [0.8, 0.5]

        results = await service.suggest_keywords_by_topic(sample_topic, similarity_threshold=0.7)

        # Only high similarity keyword should be returned
        assert len(results) == 1
        assert results[0]["keyword"] == "높은유사도"
        assert results[0]["similarity"] == 0.8

    @pytest.mark.asyncio
    async def test_repository_property(self, service):
        """저장소 속성 접근 테스트."""
        repo = service.repository
        assert repo is service._repo
        assert isinstance(repo, KeywordEmbeddingRepository)

    def test_is_initialized_property(self, service):
        """초기화 상태 속성 테스트."""
        assert service.is_initialized is False

        service._initialized = True
        assert service.is_initialized is True
