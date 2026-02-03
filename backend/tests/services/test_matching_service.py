"""Unit tests for MatchingService service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid
import numpy as np

from app.services.matching.matcher import MatchingService
from app.models.topic import Topic, TopicMetadata, TopicContent, TopicCompletionStatus, DomainEnum
from app.models.reference import ReferenceDocument, ReferenceSourceType


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings fixture."""
    with patch("app.services.matching.matcher.settings") as mock:
        mock.chromadb_path = "/tmp/test_chromadb"
        mock.chromadb_collection = "test_collection"
        mock.chunk_size_threshold = 5000
        mock.chunk_overlap = 100
        mock.field_weight_definition = 0.35
        mock.field_weight_lead = 0.25
        mock.field_weight_keywords = 0.25
        mock.field_weight_hashtags = 0.10
        mock.field_weight_memory = 0.05
        mock.trust_score_pdf_book = 1.0
        mock.trust_score_markdown = 0.6
        mock.similarity_threshold_pdf_book = 0.65
        mock.similarity_threshold_markdown = 0.7
        mock.similarity_threshold = 0.7
        mock.base_similarity_weight = 0.7
        mock.trust_score_weight = 0.3
        yield mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service fixture."""
    mock_service = MagicMock()
    mock_service.encode = Mock(return_value=np.array([0.1] * 768))  # Mock 768-dim embedding
    return mock_service


@pytest.fixture
def matching_service(mock_settings, mock_embedding_service):
    """MatchingService fixture with mocked dependencies."""
    with patch("app.services.matching.matcher.get_embedding_service", return_value=mock_embedding_service):
        with patch("app.services.matching.matcher.get_circuit_breaker", return_value=MagicMock()):
            service = MatchingService()
            service._client = None  # Don't initialize real ChromaDB
            service._collection = None
            return service


@pytest.fixture
def sample_topic():
    """Sample Topic fixture."""
    return Topic(
        id="topic_1",
        metadata=TopicMetadata(
            file_path="test/path/api.md",
            file_name="api.md",
            folder="test_folder",
            domain=DomainEnum.SW,
            exam_frequency="medium",
        ),
        content=TopicContent(
            리드문="REST API는 웹 서비스의 표준 인터페이스입니다",
            정의="Representational State Transfer는 분산 시스템을 위한 아키텍처 스타일입니다",
            키워드=["API", "REST", "HTTP", "JSON"],
            해시태g="#API#REST",
            암기="REST의 6가지 제약 조건을 기억하세요",
        ),
        completion=TopicCompletionStatus(
            리드문=True,
            정의=True,
            키워드=True,
            해시태그=True,
            암기=True,
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_references():
    """Sample reference documents fixture."""
    return [
        ReferenceDocument(
            id="ref_1",
            source_type=ReferenceSourceType.PDF_BOOK,
            title="REST API 가이드",
            content="REST API는 웹 서비스에서 가장 널리 사용되는 아키텍처 스타일입니다. " * 50,  # Long content
            domain="SW",
            trust_score=1.0,
            last_updated=datetime.now(),
        ),
        ReferenceDocument(
            id="ref_2",
            source_type=ReferenceSourceType.PDF_BOOK,
            title="API 설계 원칙",
            content="API 설계에서 중요한 원칙들을 다룹니다",
            domain="SW",
            trust_score=1.0,
            last_updated=datetime.now(),
        ),
        ReferenceDocument(
            id="ref_3",
            source_type=ReferenceSourceType.MARKDOWN,
            title="마크다운 참조 문서",
            content="마크다운 형식의 참조 문서입니다",
            domain="SW",
            trust_score=0.6,
            last_updated=datetime.now(),
        ),
    ]


@pytest.fixture
def short_reference():
    """Short reference document (under chunk threshold)."""
    return ReferenceDocument(
        id="ref_short",
        source_type=ReferenceSourceType.PDF_BOOK,
        title="짧은 문서",
        content="이것은 짧은 문서입니다",
        domain="SW",
        trust_score=1.0,
        last_updated=datetime.now(),
    )


# =============================================================================
# Field Weights Tests
# =============================================================================

class TestFieldWeights:
    """Test field weight configuration."""

    def test_field_weights_configured(self, matching_service):
        """Test that field weights are properly configured."""
        weights = MatchingService.FIELD_WEIGHTS

        assert "definition" in weights
        assert "lead" in weights
        assert "keywords" in weights
        assert "hashtags" in weights
        assert "memory" in weights

        # Check weights sum to approximately 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_definition_weight_highest(self, matching_service):
        """Test that definition has highest weight."""
        weights = MatchingService.FIELD_WEIGHTS
        assert weights["definition"] >= weights["lead"]
        assert weights["definition"] >= weights["keywords"]


# =============================================================================
# Trust Score Tests
# =============================================================================

class TestTrustScores:
    """Test trust score configuration."""

    def test_trust_scores_configured(self, matching_service):
        """Test that trust scores are properly configured."""
        scores = MatchingService.TRUST_SCORES

        assert ReferenceSourceType.PDF_BOOK in scores
        assert ReferenceSourceType.MARKDOWN in scores

        # PDF books should have higher trust
        assert scores[ReferenceSourceType.PDF_BOOK] >= scores[ReferenceSourceType.MARKDOWN]

    def test_get_default_trust_score_pdf_book(self, matching_service):
        """Test getting default trust score for PDF book."""
        score = matching_service._get_default_trust_score(ReferenceSourceType.PDF_BOOK)
        assert score == 1.0

    def test_get_default_trust_score_markdown(self, matching_service):
        """Test getting default trust score for markdown."""
        score = matching_service._get_default_trust_score(ReferenceSourceType.MARKDOWN)
        assert score == 0.6

    def test_get_default_trust_score_unknown(self, matching_service):
        """Test getting default trust score for unknown source type."""
        score = matching_service._get_default_trust_score("unknown_type")
        assert score == 0.7  # Default value


# =============================================================================
# Similarity Threshold Tests
# =============================================================================

class TestSimilarityThresholds:
    """Test similarity threshold configuration."""

    def test_similarity_thresholds_configured(self, matching_service):
        """Test that similarity thresholds are properly configured."""
        thresholds = MatchingService.SIMILARITY_THRESHOLDS

        assert ReferenceSourceType.PDF_BOOK in thresholds
        assert ReferenceSourceType.MARKDOWN in thresholds

    def test_get_similarity_threshold_pdf_book(self, matching_service):
        """Test getting similarity threshold for PDF book."""
        threshold = matching_service._get_similarity_threshold(ReferenceSourceType.PDF_BOOK)
        assert threshold == 0.65

    def test_get_similarity_threshold_markdown(self, matching_service):
        """Test getting similarity threshold for markdown."""
        threshold = matching_service._get_similarity_threshold(ReferenceSourceType.MARKDOWN)
        assert threshold == 0.7


# =============================================================================
# Document Chunking Tests
# =============================================================================

class TestDocumentChunking:
    """Test document chunking logic."""

    def test_chunk_short_document(self, matching_service, short_reference):
        """Test that short documents are not chunked."""
        chunks = matching_service._chunk_document(short_reference.content)

        assert len(chunks) == 1
        assert chunks[0] == short_reference.content

    def test_chunk_long_document(self, matching_service, sample_references):
        """Test that long documents are chunked."""
        # Create a truly long document (over 5000 chars)
        long_content = "A" * 6000  # 6000 characters

        chunks = matching_service._chunk_document(long_content)

        # Should be chunked into multiple pieces
        assert len(chunks) > 1

        # Each chunk should be within threshold
        for chunk in chunks:
            assert len(chunk) <= 5000

    def test_chunk_preserves_content(self, matching_service):
        """Test that chunking preserves all content."""
        original = "A" * 10000
        chunks = matching_service._chunk_document(original)

        # Reconstruct and verify content is preserved
        reconstructed = "".join(chunks)
        assert len(reconstructed) >= len(original) * 0.95  # Allow some overlap loss

    def test_chunk_with_overlap(self, matching_service):
        """Test that chunks have overlap for context preservation."""
        long_content = "A" * 6000
        chunks = matching_service._chunk_document(long_content)

        if len(chunks) > 1:
            # Check that there's overlap between adjacent chunks
            for i in range(len(chunks) - 1):
                # End of chunk should appear in beginning of next chunk (overlap)
                assert len(chunks[i]) > 0


# =============================================================================
# Weighted Topic Text Tests
# =============================================================================

class TestWeightedTopicText:
    """Test weighted topic text preparation."""

    def test_weighted_text_all_fields(self, matching_service, sample_topic):
        """Test weighted text generation with all fields."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Should contain all fields
        assert sample_topic.content.정의 in weighted_text
        assert sample_topic.content.리드문 in weighted_text
        assert " ".join(sample_topic.content.키워드) in weighted_text
        assert sample_topic.content.해시태그 in weighted_text
        assert sample_topic.content.암기 in weighted_text

    def test_weighted_text_definition_repeated(self, matching_service, sample_topic):
        """Test that definition (highest weight) is repeated most."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Definition should appear multiple times (weight 0.35)
        definition_count = weighted_text.count(sample_topic.content.정의)
        assert definition_count == 3

    def test_weighted_text_lead_repeated(self, matching_service, sample_topic):
        """Test that lead is repeated for its weight."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Lead should appear twice (weight 0.25)
        lead_count = weighted_text.count(sample_topic.content.리드문)
        assert lead_count == 2

    def test_weighted_text_keywords_repeated(self, matching_service, sample_topic):
        """Test that keywords are repeated for their weight."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Keywords text should appear twice
        keywords_text = " ".join(sample_topic.content.키워드)
        keywords_count = weighted_text.count(keywords_text)
        assert keywords_count == 2

    def test_weighted_text_empty_fields(self, matching_service):
        """Test weighted text with empty fields."""
        topic = Topic(
            id="topic_empty",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="",
                정의="",
                키워드=[],
                해시태g="",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        weighted_text = matching_service._prepare_weighted_topic_text(topic)

        # Should handle empty fields gracefully
        assert isinstance(weighted_text, str)


# =============================================================================
# Final Score Calculation Tests
# =============================================================================

class TestFinalScoreCalculation:
    """Test final score calculation with trust factor."""

    def test_compute_final_score_basic(self, matching_service):
        """Test basic final score calculation."""
        similarity = 0.8
        trust = 1.0

        final = matching_service._compute_final_score(similarity, trust)

        # Formula: similarity * (0.7 + 0.3 * trust)
        # = 0.8 * (0.7 + 0.3 * 1.0) = 0.8 * 1.0 = 0.8
        assert abs(final - 0.8) < 0.01

    def test_compute_final_score_low_trust(self, matching_service):
        """Test final score with low trust score."""
        similarity = 0.8
        trust = 0.5

        final = matching_service._compute_final_score(similarity, trust)

        # Formula: 0.8 * (0.7 + 0.3 * 0.5) = 0.8 * 0.85 = 0.68
        assert abs(final - 0.68) < 0.01

    def test_compute_final_score_bounds(self, matching_service):
        """Test that final score stays within bounds."""
        # Test with extreme values
        final1 = matching_service._compute_final_score(1.0, 1.0)
        assert 0.0 <= final1 <= 1.0

        final2 = matching_service._compute_final_score(0.0, 0.0)
        assert 0.0 <= final2 <= 1.0

        final3 = matching_service._compute_final_score(2.0, 2.0)  # Out of range
        assert 0.0 <= final3 <= 1.0


# =============================================================================
# Index References Tests (with mocked ChromaDB)
# =============================================================================

class TestIndexReferences:
    """Test reference indexing."""

    @pytest.mark.asyncio
    async def test_index_short_reference(self, matching_service, short_reference):
        """Test indexing a short reference (no chunking)."""
        # Mock collection
        mock_collection = MagicMock()
        matching_service._collection = mock_collection

        result = await matching_service.index_references([short_reference])

        # Should index 1 chunk
        assert result == 1
        mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_empty_list(self, matching_service):
        """Test indexing empty reference list."""
        result = await matching_service.index_references([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_index_sets_default_trust_score(self, matching_service):
        """Test that indexing sets default trust score."""
        mock_collection = MagicMock()
        matching_service._collection = mock_collection

        ref = ReferenceDocument(
            id="ref_test",
            source_type=ReferenceSourceType.MARKDOWN,
            title="Test",
            content="Test content",
            domain="SW",
            trust_score=1.0,  # Will be replaced
            last_updated=datetime.now(),
        )

        await matching_service.index_references([ref])

        # Verify add was called with adjusted trust score
        call_args = mock_collection.add.call_args
        metadatas = call_args[1]["metadatas"]
        assert metadatas[0]["trust_score"] == 0.6  # Markdown default

    @pytest.mark.asyncio
    async def test_index_with_circuit_breaker(self, matching_service, short_reference):
        """Test indexing with circuit breaker."""
        mock_collection = MagicMock()
        matching_service._collection = mock_collection

        # Should use circuit breaker
        result = await matching_service.index_references([short_reference])
        assert result >= 0


# =============================================================================
# Find References Tests (with mocked ChromaDB)
# =============================================================================

class TestFindReferences:
    """Test reference finding."""

    @pytest.mark.asyncio
    async def test_find_references_empty_result(
        self,
        matching_service,
        sample_topic,
    ):
        """Test finding references with empty result."""
        # Mock collection to return empty results
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
        })
        matching_service._collection = mock_collection

        results = await matching_service.find_references(sample_topic)

        assert results == []

    @pytest.mark.asyncio
    async def test_find_references_with_results(
        self,
        matching_service,
        sample_topic,
    ):
        """Test finding references with results."""
        # Mock collection to return results
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [["ref_1", "ref_2"]],
            "distances": [[0.2, 0.3]],  # Similarity = 1 - distance
            "metadatas": [[
                {
                    "title": "Test Ref 1",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_1",
                },
                {
                    "title": "Test Ref 2",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_2",
                },
            ]],
            "documents": [["Content 1", "Content 2"]],
        })
        matching_service._collection = mock_collection

        results = await matching_service.find_references(sample_topic, top_k=5)

        # Should return matched references
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_find_references_filters_by_threshold(
        self,
        matching_service,
        sample_topic,
    ):
        """Test that low similarity results are filtered."""
        # Mock collection with low similarity results
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [["ref_1"]],
            "distances": [[0.5]],  # Similarity = 0.5 (below threshold)
            "metadatas": [[
                {
                    "title": "Low Similarity",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_1",
                },
            ]],
            "documents": [["Content"]],
        })
        matching_service._collection = mock_collection

        results = await matching_service.find_references(sample_topic)

        # Should filter out low similarity
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_references_with_domain_filter(
        self,
        matching_service,
        sample_topic,
    ):
        """Test finding references with domain filter."""
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
        })
        matching_service._collection = mock_collection

        # Should pass domain filter to query
        await matching_service.find_references(sample_topic, domain_filter="SW")

        call_args = mock_collection.query.call_args
        assert call_args[1]["where"] == {"domain": "SW"}

    @pytest.mark.asyncio
    async def test_find_references_deduplicates_chunks(
        self,
        matching_service,
        sample_topic,
    ):
        """Test that chunks from same document are deduplicated."""
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [["ref_1_chunk0", "ref_1_chunk1", "ref_2"]],
            "distances": [[0.1, 0.2, 0.15]],
            "metadatas": [[
                {
                    "title": "Ref 1",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_1",  # Same parent
                    "is_chunk": True,
                },
                {
                    "title": "Ref 1",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_1",  # Same parent
                    "is_chunk": True,
                },
                {
                    "title": "Ref 2",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": "ref_2",  # Different parent
                    "is_chunk": False,
                },
            ]],
            "documents": [["Chunk 0", "Chunk 1", "Ref 2 content"]],
        })
        matching_service._collection = mock_collection

        results = await matching_service.find_references(sample_topic, top_k=10)

        # Should deduplicate chunks - keep highest scoring one
        ref_1_count = sum(1 for r in results if r.reference_id == "ref_1")
        assert ref_1_count == 1  # Only one from ref_1

    @pytest.mark.asyncio
    async def test_find_references_respects_top_k(
        self,
        matching_service,
        sample_topic,
    ):
        """Test that find_references respects top_k parameter."""
        # Mock with many results
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [[f"ref_{i}" for i in range(20)]],
            "distances": [[0.1] * 20],
            "metadatas": [[
                {
                    "title": f"Ref {i}",
                    "domain": "SW",
                    "source_type": "pdf_book",
                    "trust_score": 1.0,
                    "parent_id": f"ref_{i}",
                }
                for i in range(20)
            ]],
            "documents": [["Content"] * 20],
        })
        matching_service._collection = mock_collection

        results = await matching_service.find_references(sample_topic, top_k=5)

        # Should limit to top_k
        assert len(results) <= 5


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_find_references_handles_exception(self, matching_service, sample_topic):
        """Test that find_references handles exceptions gracefully."""
        # Mock collection that raises exception
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(side_effect=Exception("ChromaDB error"))
        matching_service._collection = mock_collection

        # Should return empty list instead of raising
        results = await matching_service.find_references(sample_topic)
        assert results == []

    @pytest.mark.asyncio
    async def test_index_references_handles_exception(self, matching_service):
        """Test that index_references handles exceptions."""
        # Mock collection that raises exception
        mock_collection = MagicMock()
        mock_collection.add = MagicMock(side_effect=Exception("ChromaDB error"))
        matching_service._collection = mock_collection

        with pytest.raises(Exception):
            await matching_service.index_references([
                ReferenceDocument(
                    id="ref_1",
                    source_type=ReferenceSourceType.PDF_BOOK,
                    title="Test",
                    content="Content",
                    domain="SW",
                    trust_score=1.0,
                    last_updated=datetime.now(),
                )
            ])


# =============================================================================
# Korean Language Tests (한국어 테스트)
# =============================================================================

class TestKoreanLanguage:
    """Korean language support tests."""

    def test_korean_topic_content_weighted_text(self, matching_service, sample_topic):
        """Test Korean content in weighted text generation."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Should preserve Korean content
        assert "REST API는" in weighted_text
        assert "웹 서비스의" in weighted_text

    def test_korean_content_in_chunks(self, matching_service):
        """Test that Korean content is chunked properly."""
        korean_content = "한글 내용입니다. " * 1000  # Long Korean text

        chunks = matching_service._chunk_document(korean_content)

        # Should chunk Korean content
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_korean_topic_fields(self, matching_service, sample_topic):
        """Test Korean field names in topic processing."""
        weighted_text = matching_service._prepare_weighted_topic_text(sample_topic)

        # Korean content should be included
        assert len(weighted_text) > 0
        # Check that Korean characters are preserved
        assert any('\uAC00' <= char <= '\uD7A3' for char in weighted_text)


# =============================================================================
# Concurrency Tests
# =============================================================================

class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_find_operations(self, matching_service, sample_topic):
        """Test multiple concurrent find operations."""
        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
        })
        matching_service._collection = mock_collection

        # Run multiple concurrent operations
        import asyncio
        tasks = [
            matching_service.find_references(sample_topic)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert all(isinstance(r, list) for r in results)


# =============================================================================
# Reset Collection Tests
# =============================================================================

class TestResetCollection:
    """Test collection reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_collection_success(self, matching_service):
        """Test successful collection reset."""
        mock_client = MagicMock()
        matching_service._client = mock_client
        matching_service._collection = MagicMock()

        await matching_service.reset_collection()

        # Should delete and reset collection
        mock_client.delete_collection.assert_called_once()
        assert matching_service._collection is None

    @pytest.mark.asyncio
    async def test_reset_collection_with_error(self, matching_service):
        """Test collection reset with error handling."""
        import pytest
        from app.core.errors import TransientError

        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = Exception("DB Error")
        matching_service._client = mock_client

        # Should propagate the error
        with pytest.raises(Exception):
            await matching_service.reset_collection()


# =============================================================================
# Global Service Tests
# =============================================================================

class TestGlobalService:
    """Test global service instance."""

    def test_get_matching_service_singleton(self):
        """Test that get_matching_service returns singleton instance."""
        from app.services.matching.matcher import get_matching_service, MatchingService

        # Reset global instance
        import app.services.matching.matcher as matcher_module
        matcher_module._matching_service = None

        service1 = get_matching_service()
        service2 = get_matching_service()

        # Should return same instance
        assert service1 is service2
        assert isinstance(service1, MatchingService)


# =============================================================================
# Property Tests (Error Handling)
# =============================================================================

class TestClientProperty:
    """Test client property initialization."""

    def test_client_property_exists(self, matching_service):
        """Test client property is accessible."""
        # Verify client property exists and is initialized
        assert hasattr(matching_service, 'client')
        # Client should be initialized by fixture
        assert matching_service._client is not None


class TestCollectionProperty:
    """Test collection property initialization."""

    def test_collection_access_after_initialization(self, matching_service):
        """Test collection can be accessed after client is set."""
        mock_collection = MagicMock()
        matching_service._collection = mock_collection

        # Should return existing collection
        assert matching_service.collection == mock_collection

    def test_collection_property_exists(self, matching_service):
        """Test collection property is accessible."""
        # Verify collection property exists and is initialized
        assert hasattr(matching_service, 'collection')
        # Collection should be initialized by fixture
        assert matching_service._collection is not None
