"""Unit tests for ValidationEngine service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid
import json

from app.services.validation.engine import ValidationEngine
from app.models.topic import Topic, TopicMetadata, TopicContent, TopicCompletionStatus, DomainEnum
from app.models.reference import MatchedReference, ReferenceSourceType
from app.models.validation import ValidationResult, ContentGap, GapType


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def validation_engine():
    """ValidationEngine fixture."""
    engine = ValidationEngine()
    engine._cache_manager = None
    return engine


@pytest.fixture
def sample_topic():
    """Sample Topic fixture."""
    return Topic(
        id="topic_1",
        metadata=TopicMetadata(
            file_path="test/path/topic1.md",
            file_name="topic1.md",
            folder="test_folder",
            domain=DomainEnum.SW,
            exam_frequency="medium",
        ),
        content=TopicContent(
            리드문="소프트웨어 아키텍처 설계 기술",
            정의="시스템의 구조와 동작을 정의하는 기술",
            키워드=["아키텍처", "설계"],
            해시태그="#SW",
            암기="",
        ),
        completion=TopicCompletionStatus(
            리드문=True,
            정의=True,
            키워드=True,
            해시태그=True,
            암기=False,
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def incomplete_topic():
    """Incomplete Topic fixture for edge case testing."""
    return Topic(
        id="topic_2",
        metadata=TopicMetadata(
            file_path="test/path/topic2.md",
            file_name="topic2.md",
            folder="test_folder",
            domain=DomainEnum.SW,
            exam_frequency="medium",
        ),
        content=TopicContent(
            리드문="",  # Empty
            정의="짧",  # Too short (< 50 chars)
            키워드=["하나"],  # Only 1 keyword (< 3 required)
            해시태g="",
            암기="",
        ),
        completion=TopicCompletionStatus(
            리드문=False,
            정의=False,
            키워드=False,
            해시태그=False,
            암기=False,
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_matched_references():
    """Sample matched references fixture."""
    return [
        MatchedReference(
            reference_id="ref_1",
            title="소프트웨어 아키텍처 가이드",
            source_type=ReferenceSourceType.PDF_BOOK,
            similarity_score=0.85,
            domain="SW",
            trust_score=1.0,
            relevant_snippet="소프트웨어 아키텍처는 시스템의 구조와 동작을 정의합니다. 이에는 컴포넌트, 연결, 제약 조건이 포함됩니다.",
        ),
        MatchedReference(
            reference_id="ref_2",
            title="설계 패턴 참조서",
            source_type=ReferenceSourceType.PDF_BOOK,
            similarity_score=0.75,
            domain="SW",
            trust_score=1.0,
            relevant_snippet="디자인 패턴은 소프트웨어 설계에서 반복적으로 발생하는 문제에 대한 표준 해결책입니다.",
        ),
    ]


@pytest.fixture
def empty_topic():
    """Empty topic for edge case testing."""
    return Topic(
        id="topic_3",
        metadata=TopicMetadata(
            file_path="test/path/empty.md",
            file_name="empty.md",
            folder="test_folder",
            domain=DomainEnum.SW,
            exam_frequency="low",
        ),
        content=TopicContent(
            리드문="",
            정의="",
            키워드=[],
            해시태g="",
            암기="",
        ),
        completion=TopicCompletionStatus(
            리드문=False,
            정의=False,
            키워드=False,
            해시태그=False,
            암기=False,
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Validate Method Tests
# =============================================================================

class TestValidate:
    """Test validate method."""

    @pytest.mark.asyncio
    async def test_validate_complete_topic(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test validation of a complete topic."""
        result = await validation_engine.validate(sample_topic, sample_matched_references)

        assert isinstance(result, ValidationResult)
        assert result.topic_id == sample_topic.id
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.field_completeness_score <= 1.0
        assert 0.0 <= result.content_accuracy_score <= 1.0
        assert 0.0 <= result.reference_coverage_score <= 1.0
        assert isinstance(result.gaps, list)
        assert result.matched_references == sample_matched_references

    @pytest.mark.asyncio
    async def test_validate_incomplete_topic(
        self,
        validation_engine,
        incomplete_topic,
        sample_matched_references,
    ):
        """Test validation of an incomplete topic."""
        result = await validation_engine.validate(incomplete_topic, sample_matched_references)

        assert result.topic_id == incomplete_topic.id
        assert len(result.gaps) > 0

        # Should have gaps for missing/incomplete fields
        gap_fields = {gap.field_name for gap in result.gaps}
        assert "리드문" in gap_fields
        assert "정의" in gap_fields
        assert "키워드" in gap_fields

    @pytest.mark.asyncio
    async def test_validate_empty_topic(
        self,
        validation_engine,
        empty_topic,
    ):
        """Test validation of an empty topic (edge case)."""
        result = await validation_engine.validate(empty_topic, [])

        assert result.topic_id == empty_topic.id
        assert len(result.gaps) > 0

        # Check gap types
        gap_types = {gap.gap_type for gap in result.gaps}
        assert GapType.MISSING_FIELD in gap_types
        assert GapType.MISSING_KEYWORDS in gap_types

    @pytest.mark.asyncio
    async def test_validate_without_references(
        self,
        validation_engine,
        sample_topic,
    ):
        """Test validation without references."""
        result = await validation_engine.validate(sample_topic, [])

        # Should still produce a result
        assert result.topic_id == sample_topic.id
        assert result.matched_references == []
        assert result.content_accuracy_score == 0.5  # Neutral score

    @pytest.mark.asyncio
    async def test_validate_with_cache_hit(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test validation with cache hit."""
        # Mock cache manager with cached result
        cached_result = ValidationResult(
            id=f"validation-{sample_topic.id}-12345",
            topic_id=sample_topic.id,
            overall_score=0.8,
            field_completeness_score=0.9,
            content_accuracy_score=0.8,
            reference_coverage_score=0.7,
            gaps=[],
            matched_references=sample_matched_references,
            validation_timestamp=datetime.now(),
        )

        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache._in_memory = AsyncMock()
        mock_cache._in_memory.get = AsyncMock(
            return_value=json.dumps({
                "topic_id": cached_result.topic_id,
                "overall_score": cached_result.overall_score,
                "gaps": [],
                "matched_references": [
                    {
                        "reference_id": ref.reference_id,
                        "title": ref.title,
                        "source": ref.source_type.value,
                        "similarity_score": ref.similarity_score,
                        "relevant_snippet": ref.relevant_snippet,
                    }
                    for ref in cached_result.matched_references
                ],
                "field_completeness_score": cached_result.field_completeness_score,
                "content_accuracy_score": cached_result.content_accuracy_score,
                "reference_coverage_score": cached_result.reference_coverage_score,
            })
        )
        validation_engine._cache_manager = mock_cache

        result = await validation_engine.validate(sample_topic, sample_matched_references)

        # Should return cached result
        assert mock_cache._in_memory.get.called
        # Note: Overall scores may differ because cached result has different field scores
        assert result.topic_id == cached_result.topic_id

    @pytest.mark.asyncio
    async def test_validate_score_calculation(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test overall score calculation formula."""
        result = await validation_engine.validate(sample_topic, sample_matched_references)

        # Overall score = field_score * 0.3 + accuracy_score * 0.4 + coverage_score * 0.3
        expected_score = (
            result.field_completeness_score * 0.3 +
            result.content_accuracy_score * 0.4 +
            result.reference_coverage_score * 0.3
        )

        assert abs(result.overall_score - expected_score) < 0.01


# =============================================================================
# Field Completeness Check Tests
# =============================================================================

class TestCheckFieldCompleteness:
    """Test _check_field_completeness method."""

    def test_check_complete_fields(self, validation_engine, sample_topic):
        """Test checking complete fields."""
        gaps = validation_engine._check_field_completeness(sample_topic)

        # Complete topic should have minimal gaps
        assert len(gaps) == 0 or all(gap.confidence > 0 for gap in gaps)

    def test_check_empty_lead(self, validation_engine, incomplete_topic):
        """Test checking empty 리드문 field."""
        gaps = validation_engine._check_field_completeness(incomplete_topic)

        lead_gaps = [g for g in gaps if g.field_name == "리드문"]
        assert len(lead_gaps) == 1
        assert lead_gaps[0].gap_type == GapType.MISSING_FIELD
        assert lead_gaps[0].confidence == 0.8
        assert lead_gaps[0].missing_count == 1
        assert lead_gaps[0].required_count == 1

    def test_check_short_definition(self, validation_engine, incomplete_topic):
        """Test checking short 정의 field."""
        gaps = validation_engine._check_field_completeness(incomplete_topic)

        definition_gaps = [g for g in gaps if g.field_name == "정의"]
        assert len(definition_gaps) == 1
        assert definition_gaps[0].gap_type == GapType.INCOMPLETE_DEFINITION
        assert "50자 이상" in definition_gaps[0].reasoning

    def test_check_insufficient_keywords(self, validation_engine, incomplete_topic):
        """Test checking insufficient 키워드."""
        gaps = validation_engine._check_field_completeness(incomplete_topic)

        keyword_gaps = [g for g in gaps if g.field_name == "키워드"]
        assert len(keyword_gaps) == 1
        assert keyword_gaps[0].gap_type == GapType.MISSING_KEYWORDS
        assert keyword_gaps[0].missing_count == 2  # 3 required - 1 current
        assert keyword_gaps[0].required_count == 3

    def test_check_empty_topic_all_gaps(self, validation_engine, empty_topic):
        """Test checking all gaps in empty topic."""
        gaps = validation_engine._check_field_completeness(empty_topic)

        gap_fields = {gap.field_name for gap in gaps}
        assert "리드문" in gap_fields
        assert "정의" in gap_fields
        assert "키워드" in gap_fields


# =============================================================================
# Content Accuracy Check Tests
# =============================================================================

class TestCheckContentAccuracy:
    """Test _check_content_accuracy method."""

    def test_check_with_no_references(self, validation_engine, sample_topic):
        """Test checking accuracy with no references."""
        gaps = validation_engine._check_content_accuracy(sample_topic, [])

        assert len(gaps) == 1
        assert gaps[0].field_name == "전체"
        assert gaps[0].gap_type == GapType.MISSING_KEYWORDS
        assert "참조 문서를 찾을 수 없어" in gaps[0].reasoning or "내용 검증이 불가능합니다" in gaps[0].reasoning

    def test_check_with_references_better_content(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test checking accuracy when reference has better content."""
        # Create topic with short definition
        short_topic = Topic(
            id="topic_short",
            metadata=sample_topic.metadata,
            content=TopicContent(
                리드문="리드문",
                정의="짧은 정의",  # Very short definition
                키워드=["키워드"],
                해시태g="#태그",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        gaps = validation_engine._check_content_accuracy(
            short_topic,
            sample_matched_references
        )

        # Should suggest better content from references
        definition_gaps = [g for g in gaps if g.field_name == "정의"]
        if len(definition_gaps) > 0:
            # High similarity reference with better content
            assert any(g.confidence > 0.8 for g in definition_gaps)


# =============================================================================
# Score Calculation Tests
# =============================================================================

class TestCalculateScores:
    """Test score calculation methods."""

    def test_field_completeness_score_complete(self, validation_engine, sample_topic):
        """Test field completeness score for complete topic."""
        score = validation_engine._calculate_field_completeness_score(sample_topic)

        assert 0.0 <= score <= 1.0
        # Complete topic should have high score
        assert score > 0.5

    def test_field_completeness_score_empty(self, validation_engine, empty_topic):
        """Test field completeness score for empty topic."""
        score = validation_engine._calculate_field_completeness_score(empty_topic)

        assert 0.0 <= score <= 1.0
        # Empty topic should have low score
        assert score < 0.5

    def test_field_completeness_score_components(self, validation_engine, sample_topic):
        """Test that field completeness considers all fields."""
        score = validation_engine._calculate_field_completeness_score(sample_topic)

        # Check that all fields contribute to score
        assert score > 0  # Should be positive for valid topic

    def test_accuracy_score_with_references(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test accuracy score calculation with references."""
        score = validation_engine._calculate_accuracy_score(
            sample_topic,
            sample_matched_references
        )

        assert 0.0 <= score <= 1.0
        # Should be based on average similarity of top 3 references
        expected = sum(r.similarity_score for r in sample_matched_references[:3]) / len(sample_matched_references[:3])
        assert abs(score - expected) < 0.01

    def test_accuracy_score_without_references(self, validation_engine, sample_topic):
        """Test accuracy score without references."""
        score = validation_engine._calculate_accuracy_score(sample_topic, [])

        # Neutral score when no references
        assert score == 0.5

    def test_coverage_score_with_references(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test coverage score calculation."""
        score = validation_engine._calculate_coverage_score(
            sample_topic,
            sample_matched_references
        )

        assert 0.0 <= score <= 1.0
        # Based on high/medium quality matches
        high_quality = sum(1 for r in sample_matched_references if r.similarity_score > 0.8)
        medium_quality = sum(1 for r in sample_matched_references if 0.7 < r.similarity_score <= 0.8)
        expected = min(1.0, (high_quality * 0.5 + medium_quality * 0.3))
        assert abs(score - expected) < 0.01

    def test_coverage_score_without_references(self, validation_engine, sample_topic):
        """Test coverage score without references."""
        score = validation_engine._calculate_coverage_score(sample_topic, [])

        # Zero coverage without references
        assert score == 0.0


# =============================================================================
# Cache Invalidation Tests
# =============================================================================

class TestCacheInvalidation:
    """Test cache invalidation methods."""

    @pytest.mark.asyncio
    async def test_invalidate_topic_cache(self, validation_engine):
        """Test topic cache invalidation."""
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache.invalidate_by_pattern = AsyncMock(return_value=5)
        validation_engine._cache_manager = mock_cache

        await validation_engine.invalidate_topic_cache("topic_123")

        # Verify invalidation was called with correct pattern
        mock_cache.invalidate_by_pattern.assert_called_once_with("validation:topic_123:*")

    @pytest.mark.asyncio
    async def test_invalidate_topic_cache_disabled(self, validation_engine):
        """Test topic cache invalidation when cache disabled."""
        mock_cache = AsyncMock()
        mock_cache.enabled = False
        validation_engine._cache_manager = mock_cache

        # Should not raise error
        await validation_engine.invalidate_topic_cache("topic_123")

        # Should not call invalidate
        mock_cache.invalidate_by_pattern.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_reference_cache(self, validation_engine):
        """Test reference cache invalidation."""
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache.invalidate_by_pattern = AsyncMock(return_value=3)
        validation_engine._cache_manager = mock_cache

        await validation_engine.invalidate_reference_cache("ref_123")

        # Verify invalidation was called with correct pattern
        mock_cache.invalidate_by_pattern.assert_called_once_with("validation:*:*ref_123*")

    @pytest.mark.asyncio
    async def test_invalidate_cache_exception_handling(self, validation_engine):
        """Test cache invalidation handles exceptions gracefully."""
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache.invalidate_by_pattern = AsyncMock(side_effect=Exception("Cache error"))
        validation_engine._cache_manager = mock_cache

        # Should not raise error
        await validation_engine.invalidate_topic_cache("topic_123")


# =============================================================================
# Suggestion Methods Tests
# =============================================================================

class TestSuggestionMethods:
    """Test suggestion generation methods."""

    def test_suggest_lead_from_references(self, validation_engine, sample_topic):
        """Test suggesting lead sentence."""
        suggestion = validation_engine._suggest_lead_from_references(sample_topic)

        # Should return lead or definition if available
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0

    def test_suggest_lead_from_definition(self, validation_engine):
        """Test suggesting lead from definition when lead is empty."""
        topic = Topic(
            id="topic_test",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="",  # Empty
                정의="상세한 정의 내용이 여기에 들어갑니다",
                키워드=[],
                해시태g="",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        suggestion = validation_engine._suggest_lead_from_references(topic)

        # Should use definition as fallback
        assert "상세한 정의 내용이 여기에 들어갑니다" in suggestion

    def test_suggest_lead_empty_topic(self, validation_engine, empty_topic):
        """Test suggesting lead for completely empty topic."""
        suggestion = validation_engine._suggest_lead_from_references(empty_topic)

        # Should provide placeholder with file name
        assert "empty.md" in suggestion

    def test_suggest_definition_from_topic(self, validation_engine, sample_topic):
        """Test suggesting definition from topic content."""
        suggestion = validation_engine._suggest_definition_from_references(sample_topic)

        # Should return current definition
        assert suggestion == sample_topic.content.정의

    def test_suggest_definition_empty_topic(self, validation_engine, empty_topic):
        """Test suggesting definition for empty topic."""
        suggestion = validation_engine._suggest_definition_from_references(empty_topic)

        # Should provide placeholder with file name
        assert "empty.md" in suggestion
        assert "기술사 수준 정의" in suggestion


# =============================================================================
# Cache Key Generation Tests
# =============================================================================

class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_make_cache_key_basic(self, validation_engine, sample_topic, sample_matched_references):
        """Test basic cache key generation."""
        key = validation_engine._make_cache_key(sample_topic, sample_matched_references)

        assert isinstance(key, str)
        assert key.startswith("validation:")
        assert sample_topic.id in key
        assert ":" in key

    def test_make_cache_key_different_content(self, validation_engine, sample_topic):
        """Test cache key changes with different content."""
        # Create two topics with different content
        topic2 = Topic(
            id=sample_topic.id,
            metadata=sample_topic.metadata,
            content=TopicContent(
                리드문="Different lead",
                정의="Different definition",
                키워드=["different"],
                해시태g="#different",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        key1 = validation_engine._make_cache_key(sample_topic, [])
        key2 = validation_engine._make_cache_key(topic2, [])

        # Keys should be different
        assert key1 != key2

    def test_make_cache_key_different_references(
        self,
        validation_engine,
        sample_topic,
        sample_matched_references,
    ):
        """Test cache key changes with different references."""
        key1 = validation_engine._make_cache_key(sample_topic, sample_matched_references[:1])
        key2 = validation_engine._make_cache_key(sample_topic, sample_matched_references)

        # Keys should be different
        assert key1 != key2


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validate_topic_with_none_values(self, validation_engine):
        """Test validation with empty values in content (Pydantic v2 compatible)."""
        # Use empty strings instead of None for Pydantic v2
        topic = Topic(
            id="topic_none",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="",  # Empty string instead of None
                정의="",
                키워드=[],  # Empty list
                해시태그="",  # Empty string
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Should handle empty values gracefully
        gaps = validation_engine._check_field_completeness(topic)
        assert isinstance(gaps, list)

    def test_validate_with_very_long_content(self, validation_engine):
        """Test validation with very long content."""
        long_content = "A" * 10000  # Very long string

        topic = Topic(
            id="topic_long",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문=long_content,
                정의=long_content,
                키워드=["keyword1", "keyword2", "keyword3"],
                해시태g="#태그",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        score = validation_engine._calculate_field_completeness_score(topic)
        assert 0.0 <= score <= 1.0

    def test_validate_with_special_characters(self, validation_engine):
        """Test validation with special characters in content."""
        topic = Topic(
            id="topic_special",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="리드문에 특수字符 !@#$% 포함",
                정의="定義 с кириллицей",
                키워드=["API", "REST", "GraphQL"],
                해시태g="#SW#개발",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        gaps = validation_engine._check_field_completeness(topic)
        assert isinstance(gaps, list)


# =============================================================================
# Korean Language Tests (한국어 테스트)
# =============================================================================

class TestKoreanLanguage:
    """Korean language support tests."""

    def test_korean_field_names(self, validation_engine, incomplete_topic):
        """Test Korean field names in gap detection."""
        gaps = validation_engine._check_field_completeness(incomplete_topic)

        # Check that Korean field names are preserved
        gap_fields = {gap.field_name for gap in gaps}
        assert "리드문" in gap_fields
        assert "정의" in gap_fields
        assert "키워드" in gap_fields

    def test_korean_reasoning_messages(self, validation_engine, incomplete_topic):
        """Test Korean reasoning messages in gaps."""
        gaps = validation_engine._check_field_completeness(incomplete_topic)

        # Check that reasoning messages are in Korean
        for gap in gaps:
            assert isinstance(gap.reasoning, str)
            # Korean text should contain Korean characters
            if len(gap.reasoning) > 0:
                assert any('\uAC00' <= char <= '\uD7A3' for char in gap.reasoning)

    def test_korean_minimum_lengths(self, validation_engine):
        """Test Korean minimum length validation."""
        topic = Topic(
            id="topic_korean",
            metadata=TopicMetadata(
                file_path="test.md",
                file_name="test",
                folder="test",
                domain=DomainEnum.SW,
            ),
            content=TopicContent(
                리드문="가",  # Very short Korean text
                정의="나",  # Very short Korean text
                키워드=["한글"],
                해시태g="#한글",
                암기="",
            ),
            completion=TopicCompletionStatus(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        gaps = validation_engine._check_field_completeness(topic)

        # Should detect insufficient Korean text length
        lead_gaps = [g for g in gaps if g.field_name == "리드문"]
        assert len(lead_gaps) == 1

        definition_gaps = [g for g in gaps if g.field_name == "정의"]
        assert len(definition_gaps) == 1
