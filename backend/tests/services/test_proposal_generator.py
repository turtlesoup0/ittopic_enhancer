"""Unit tests for ProposalGenerator service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid
import json

from app.services.proposal.generator import ProposalGenerator, KeywordScore
from app.models.validation import ValidationResult, ContentGap, GapType
from app.models.proposal import EnhancementProposal, ProposalPriority
from app.models.reference import MatchedReference, ReferenceSourceType


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def proposal_generator():
    """ProposalGenerator fixture without OpenAI client."""
    with patch("app.services.proposal.generator.settings"):
        generator = ProposalGenerator()
        generator.client = None  # No OpenAI client for unit tests
        generator._circuit_breaker = None
        generator._cache_manager = None
        return generator


@pytest.fixture
def sample_validation_result():
    """Sample ValidationResult fixture."""
    return ValidationResult(
        id=str(uuid.uuid4()),
        topic_id="test_topic_1",
        overall_score=0.65,
        field_completeness_score=0.7,
        content_accuracy_score=0.6,
        reference_coverage_score=0.65,
        gaps=[
            ContentGap(
                gap_type=GapType.MISSING_FIELD,
                field_name="리드문",
                current_value="",
                suggested_value="리드문 제안 내용",
                confidence=0.8,
                reference_id="ref_1",
                reasoning="리드문이 비어있습니다",
            ),
            ContentGap(
                gap_type=GapType.INCOMPLETE_DEFINITION,
                field_name="정의",
                current_value="짧은 정의",
                suggested_value="상세한 정의 제안",
                confidence=0.9,
                reference_id="ref_1",
                reasoning="정의가 불충분합니다",
            ),
            ContentGap(
                gap_type=GapType.MISSING_KEYWORDS,
                field_name="키워드",
                current_value="AI",
                suggested_value="",
                confidence=0.85,
                reference_id="",
                reasoning="핵심 키워드가 부족합니다",
            ),
        ],
        matched_references=[
            MatchedReference(
                reference_id="ref_1",
                title="테스트 참조 문서",
                source_type=ReferenceSourceType.PDF_BOOK,
                similarity_score=0.85,
                domain="SW",
                trust_score=1.0,
                relevant_snippet="관련 내용",
            ),
        ],
        validation_timestamp=datetime.now(),
    )


@pytest.fixture
def high_score_validation_result():
    """High score validation result (no gaps)."""
    return ValidationResult(
        id=str(uuid.uuid4()),
        topic_id="test_topic_2",
        overall_score=0.95,
        field_completeness_score=0.95,
        content_accuracy_score=0.95,
        reference_coverage_score=0.95,
        gaps=[],  # No gaps
        matched_references=[],
        validation_timestamp=datetime.now(),
    )


# =============================================================================
# Generate Proposals Tests
# =============================================================================

class TestGenerateProposals:
    """Test generate_proposals method."""

    @pytest.mark.asyncio
    async def test_generate_proposals_with_gaps(
        self,
        proposal_generator,
        sample_validation_result,
    ):
        """Test proposal generation from validation result with gaps."""
        proposals = await proposal_generator.generate_proposals(sample_validation_result)

        assert len(proposals) == 3
        assert all(isinstance(p, EnhancementProposal) for p in proposals)

        # Check first proposal (missing field)
        assert proposals[0].priority == ProposalPriority.CRITICAL
        assert "리드문" in proposals[0].title
        assert proposals[0].estimated_effort == 20
        assert proposals[0].estimated_effort == 20

    @pytest.mark.asyncio
    async def test_generate_proposals_no_gaps_high_score(
        self,
        proposal_generator,
        high_score_validation_result,
    ):
        """Test proposal generation with no gaps but high overall score (>0.9)."""
        proposals = await proposal_generator.generate_proposals(high_score_validation_result)

        # Should not generate improvement suggestion if score >= 0.9
        assert len(proposals) == 0

    @pytest.mark.asyncio
    async def test_generate_proposals_no_gaps_medium_score(
        self,
        proposal_generator,
    ):
        """Test proposal generation with no gaps and medium overall score (<0.9)."""
        validation_result = ValidationResult(
            id=str(uuid.uuid4()),
            topic_id="test_topic_3",
            overall_score=0.85,  # Less than 0.9
            field_completeness_score=0.85,
            content_accuracy_score=0.85,
            reference_coverage_score=0.85,
            gaps=[],
            matched_references=[],
            validation_timestamp=datetime.now(),
        )

        proposals = await proposal_generator.generate_proposals(validation_result)

        # Should generate improvement suggestion
        assert len(proposals) == 1
        assert proposals[0].priority == ProposalPriority.LOW
        assert "보강" in proposals[0].title
        assert proposals[0].estimated_effort == 15
        assert proposals[0].confidence == 0.6

    @pytest.mark.asyncio
    async def test_generate_proposals_duplicate_field_skipped(
        self,
        proposal_generator,
    ):
        """Test that duplicate field gaps are skipped."""
        validation_result = ValidationResult(
            id=str(uuid.uuid4()),
            topic_id="test_topic_4",
            overall_score=0.6,
            field_completeness_score=0.6,
            content_accuracy_score=0.6,
            reference_coverage_score=0.6,
            gaps=[
                ContentGap(
                    gap_type=GapType.MISSING_FIELD,
                    field_name="리드문",
                    current_value="",
                    suggested_value="제안 1",
                    confidence=0.8,
                    reference_id="ref_1",
                    reasoning="첫 번째 gap",
                ),
                ContentGap(
                    gap_type=GapType.INCOMPLETE_DEFINITION,
                    field_name="리드문",  # Same field name
                    current_value="",
                    suggested_value="제안 2",
                    confidence=0.7,
                    reference_id="ref_2",
                    reasoning="두 번째 gap (무시되어야 함)",
                ),
                ContentGap(
                    gap_type=GapType.MISSING_KEYWORDS,
                    field_name="정의",
                    current_value="",
                    suggested_value="",
                    confidence=0.9,
                    reference_id="",
                    reasoning="세 번째 gap",
                ),
            ],
            matched_references=[],
            validation_timestamp=datetime.now(),
        )

        proposals = await proposal_generator.generate_proposals(validation_result)

        # Should only generate 2 proposals (second 리드문 gap skipped)
        assert len(proposals) == 2


# =============================================================================
# Priority Determination Tests
# =============================================================================

class TestDeterminePriority:
    """Test _determine_priority method."""

    def test_priority_missing_field(self, proposal_generator):
        """Test CRITICAL priority for missing field."""
        gap = ContentGap(
            gap_type=GapType.MISSING_FIELD,
            field_name="리드문",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        priority = proposal_generator._determine_priority(gap)
        assert priority == ProposalPriority.CRITICAL

    def test_priority_incomplete_definition(self, proposal_generator):
        """Test HIGH priority for incomplete definition."""
        gap = ContentGap(
            gap_type=GapType.INCOMPLETE_DEFINITION,
            field_name="정의",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        priority = proposal_generator._determine_priority(gap)
        assert priority == ProposalPriority.HIGH

    def test_priority_missing_keywords(self, proposal_generator):
        """Test HIGH priority for missing keywords."""
        gap = ContentGap(
            gap_type=GapType.MISSING_KEYWORDS,
            field_name="키워드",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        priority = proposal_generator._determine_priority(gap)
        assert priority == ProposalPriority.HIGH

    def test_priority_outdated_content(self, proposal_generator):
        """Test MEDIUM priority for outdated content."""
        gap = ContentGap(
            gap_type=GapType.OUTDATED_CONTENT,
            field_name="정의",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        priority = proposal_generator._determine_priority(gap)
        assert priority == ProposalPriority.MEDIUM

    def test_priority_inaccurate_info(self, proposal_generator):
        """Test CRITICAL priority for inaccurate info."""
        gap = ContentGap(
            gap_type=GapType.INACCURATE_INFO,
            field_name="정의",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        priority = proposal_generator._determine_priority(gap)
        assert priority == ProposalPriority.CRITICAL


# =============================================================================
# Title and Description Generation Tests
# =============================================================================

class TestGenerateTitleAndDescription:
    """Test title and description generation methods."""

    def test_generate_title_missing_field(self, proposal_generator):
        """Test title for missing field gap."""
        gap = ContentGap(
            gap_type=GapType.MISSING_FIELD,
            field_name="리드문",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        title = proposal_generator._generate_title(gap)
        assert "리드문" in title
        assert "누락" in title or "필드" in title

    def test_generate_title_incomplete_definition(self, proposal_generator):
        """Test title for incomplete definition gap."""
        gap = ContentGap(
            gap_type=GapType.INCOMPLETE_DEFINITION,
            field_name="정의",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        title = proposal_generator._generate_title(gap)
        assert "정의" in title
        assert "보강" in title or "내용" in title

    def test_generate_description(self, proposal_generator):
        """Test description generation."""
        gap = ContentGap(
            gap_type=GapType.MISSING_FIELD,
            field_name="리드문",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        description = proposal_generator._generate_description(gap)
        assert "리드문" in description
        assert len(description) > 0


# =============================================================================
# Effort Estimation Tests
# =============================================================================

class TestEstimateEffort:
    """Test effort estimation."""

    def test_effort_missing_field(self, proposal_generator):
        """Test effort estimation for missing field."""
        gap = ContentGap(
            gap_type=GapType.MISSING_FIELD,
            field_name="리드문",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        effort = proposal_generator._estimate_effort(gap)
        assert effort == 20

    def test_effort_incomplete_definition(self, proposal_generator):
        """Test effort estimation for incomplete definition."""
        gap = ContentGap(
            gap_type=GapType.INCOMPLETE_DEFINITION,
            field_name="정의",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        effort = proposal_generator._estimate_effort(gap)
        assert effort == 30

    def test_effort_missing_keywords(self, proposal_generator):
        """Test effort estimation for missing keywords."""
        gap = ContentGap(
            gap_type=GapType.MISSING_KEYWORDS,
            field_name="키워드",
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="",
        )
        effort = proposal_generator._estimate_effort(gap)
        assert effort == 10


# =============================================================================
# Keyword Generation Tests (with Mock)
# =============================================================================

class TestGenerateKeywordsWithLLM:
    """Test generate_keywords_with_llm method."""

    @pytest.mark.asyncio
    async def test_generate_keywords_without_llm_fallback(
        self,
        proposal_generator,
    ):
        """Test keyword generation falls back to domain extraction when no LLM."""
        # Ensure no LLM client
        proposal_generator.client = None

        # Add some domain terms for testing
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 8, "related_terms": ["REST API"]},
                    {"term": "데이터베이스", "priority": 7, "related_terms": ["DB"]},
                ]
            }
        }

        keywords = await proposal_generator.generate_keywords_with_llm(
            topic_name="API 설계",
            current_content="REST API는 웹 서비스에서 사용하는 인터페이스입니다",
            field_name="정의",
            topic_id="test_1",
        )

        # Should return domain-based keywords
        assert isinstance(keywords, list)
        assert len(keywords) >= 0

    @pytest.mark.asyncio
    async def test_generate_keywords_caching(
        self,
        proposal_generator,
    ):
        """Test keyword caching with in-memory cache."""
        # Mock cache manager
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache._ttl = MagicMock()
        mock_cache._ttl.LLM_RESPONSE = 3600
        mock_cache._in_memory = AsyncMock()
        mock_cache._in_memory.get = AsyncMock(return_value=None)
        mock_cache._in_memory.set = AsyncMock()
        proposal_generator._cache_manager = mock_cache

        # No LLM client - should use fallback
        proposal_generator.client = None
        proposal_generator._domain_terms = {}

        keywords = await proposal_generator.generate_keywords_with_llm(
            topic_name="Test",
            current_content="Test content",
            field_name="정의",
            topic_id="test_1",
        )

        # Verify cache was checked
        assert mock_cache._in_memory.get.called

    @pytest.mark.asyncio
    async def test_generate_keywords_cache_hit(
        self,
        proposal_generator,
    ):
        """Test keyword generation with cache hit."""
        cached_keywords = ["API", "REST", "HTTP"]
        cached_data = json.dumps({"keywords": cached_keywords})

        # Mock cache manager with cache hit
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache._in_memory = AsyncMock()
        mock_cache._in_memory.get = AsyncMock(return_value=cached_data)
        proposal_generator._cache_manager = mock_cache

        keywords = await proposal_generator.generate_keywords_with_llm(
            topic_name="API 설계",
            current_content="REST API는 웹 서비스에서 사용하는 인터페이스입니다",
            field_name="정의",
            topic_id="test_1",
        )

        # Should return cached keywords
        assert keywords == cached_keywords


# =============================================================================
# Domain-based Keyword Extraction Tests
# =============================================================================

class TestDomainKeywordExtraction:
    """Test domain-based keyword extraction (fallback)."""

    def test_extract_keywords_from_domain(self, proposal_generator):
        """Test extracting keywords from domain terms."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 9, "related_terms": []},
                    {"term": "REST", "priority": 8, "related_terms": []},
                    {"term": "데이터베이스", "priority": 7, "related_terms": []},
                ]
            }
        }

        content = "REST API는 웹 서비스에서 데이터를 주고받는 인터페이스입니다"

        keywords = proposal_generator._extract_keywords_from_domain(content)

        # Should find matching keywords
        assert isinstance(keywords, list)
        assert "API" in keywords
        assert "REST" in keywords

    def test_extract_keywords_empty_domain_terms(self, proposal_generator):
        """Test extracting keywords with no domain terms."""
        proposal_generator._domain_terms = {}

        keywords = proposal_generator._extract_keywords_from_domain("Sample content")

        # Should return empty list
        assert keywords == []

    def test_extract_keywords_no_matches(self, proposal_generator):
        """Test extracting keywords when content has no matches."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 9, "related_terms": []},
                ]
            }
        }

        keywords = proposal_generator._extract_keywords_from_domain("관련 없는 내용입니다")

        # Should return empty list
        assert keywords == []


# =============================================================================
# Keyword Scoring Tests
# =============================================================================

class TestKeywordScoring:
    """Test keyword scoring methods."""

    def test_score_keywords_filters_stopwords(self, proposal_generator):
        """Test that stopwords are filtered out."""
        proposal_generator._stopwords = {"및", "위한", "통해"}

        keywords = ["API", "및", "REST", "위한"]
        scored = proposal_generator._score_keywords(keywords, "Test Topic")

        # Stopwords should be filtered
        assert len(scored) == 2
        assert all(kw.keyword not in ["및", "위한"] for kw in scored)

    def test_calculate_keyword_score_structure(self, proposal_generator):
        """Test keyword score returns KeywordScore with all fields."""
        proposal_generator._domain_terms = {}
        proposal_generator._compound_terms = {}
        proposal_generator._stopwords = set()

        score = proposal_generator._calculate_keyword_score("API", "Test Topic")

        assert isinstance(score, KeywordScore)
        assert score.keyword == "API"
        assert 0.0 <= score.domain_relevance <= 1.0
        assert 0.0 <= score.exam_frequency <= 1.0
        assert 0.0 <= score.originality <= 1.0
        assert 0.0 <= score.total_score <= 1.0
        assert isinstance(score.category, str)

    def test_calculate_domain_relevance_exact_match(self, proposal_generator):
        """Test domain relevance for exact match."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 10, "related_terms": []},
                ]
            }
        }

        relevance = proposal_generator._calculate_domain_relevance("API")
        assert relevance == 1.0  # Priority 10 / 10 = 1.0

    def test_calculate_domain_relevance_related_term(self, proposal_generator):
        """Test domain relevance for related term."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 8, "related_terms": ["REST API", "GraphQL"]},
                ]
            }
        }

        relevance = proposal_generator._calculate_domain_relevance("REST API")
        assert relevance == 0.7  # Related term score

    def test_calculate_domain_relevance_no_match(self, proposal_generator):
        """Test domain relevance for unknown term."""
        proposal_generator._domain_terms = {}
        proposal_generator._compound_terms = {}

        relevance = proposal_generator._calculate_domain_relevance("UnknownTerm")
        assert relevance == 0.3  # Default low relevance

    def test_categorize_keyword_domain_match(self, proposal_generator):
        """Test keyword categorization with domain match."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 8, "related_terms": []},
                ]
            }
        }

        category = proposal_generator._categorize_keyword("API")
        assert category == "SW"

    def test_categorize_keyword_compound_term(self, proposal_generator):
        """Test keyword categorization with compound term."""
        proposal_generator._compound_terms = {"TCP/IP": "네트워크"}

        category = proposal_generator._categorize_keyword("TCP/IP")
        assert category == "네트워크"

    def test_categorize_keyword_unknown(self, proposal_generator):
        """Test keyword categorization for unknown term."""
        proposal_generator._domain_terms = {}
        proposal_generator._compound_terms = {}

        category = proposal_generator._categorize_keyword("UnknownTerm")
        assert category == "기타"


# =============================================================================
# Korean Language Tests (한국어 테스트)
# =============================================================================

class TestKoreanLanguage:
    """Korean language support tests."""

    def test_korean_field_names_in_gaps(self, proposal_generator):
        """Test Korean field names are handled correctly."""
        gap = ContentGap(
            gap_type=GapType.MISSING_FIELD,
            field_name="리드문",  # Korean field name
            current_value="",
            suggested_value="",
            confidence=0.8,
            reference_id="",
            reasoning="리드문이 필요합니다",
        )

        title = proposal_generator._generate_title(gap)
        description = proposal_generator._generate_description(gap)

        assert "리드문" in title
        assert "리드문" in description

    def test_korean_topic_content_for_keywords(self, proposal_generator):
        """Test Korean content processing for keyword extraction."""
        proposal_generator._domain_terms = {
            "SW": {
                "terms": [
                    {"term": "API", "priority": 8, "related_terms": []},
                    {"term": "데이터베이스", "priority": 7, "related_terms": ["DB"]},
                ]
            }
        }

        content = "REST API는 웹 서비스에서 데이터를 주고받는 인터페이스입니다"

        keywords = proposal_generator._extract_keywords_from_domain(content)

        # Should extract keywords regardless of Korean context
        assert isinstance(keywords, list)

    @pytest.mark.asyncio
    async def test_korean_prompt_building(self, proposal_generator):
        """Test LLM prompt building with Korean content."""
        prompt = proposal_generator._build_keyword_prompt(
            topic_name="인공지능",
            current_content="기계가 인간의 지능을 모방하는 기술입니다",
            field_name="정의",
        )

        assert "인공지능" in prompt
        assert "정의" in prompt
        assert len(prompt) > 0


# =============================================================================
# Error Handling Tests (Non-LLM)
# =============================================================================

class TestErrorHandling:
    """Test error handling in proposal generator."""

    @pytest.mark.asyncio
    async def test_cache_error_fallback(self, proposal_generator):
        """Test that cache errors are handled gracefully."""
        # Mock cache that raises exception
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache._in_memory = AsyncMock()
        mock_cache._in_memory.get = AsyncMock(side_effect=Exception("Cache error"))
        mock_cache._in_memory.set = AsyncMock()
        proposal_generator._cache_manager = mock_cache
        proposal_generator.client = None
        proposal_generator._domain_terms = {}

        # Should handle cache error and fall back to domain extraction
        keywords = await proposal_generator.generate_keywords_with_llm(
            topic_name="Test",
            current_content="Test content",
            field_name="정의",
            topic_id="test_1",
        )

        # Should return empty list from domain extraction (no domain terms)
        assert isinstance(keywords, list)

    @pytest.mark.asyncio
    async def test_cache_json_parse_error(self, proposal_generator):
        """Test that invalid JSON in cache is handled gracefully."""
        # Mock cache with invalid JSON
        mock_cache = AsyncMock()
        mock_cache.enabled = True
        mock_cache._in_memory = AsyncMock()
        mock_cache._in_memory.get = AsyncMock(return_value="invalid json{{{")
        mock_cache._in_memory.set = AsyncMock()
        proposal_generator._cache_manager = mock_cache
        proposal_generator.client = None
        proposal_generator._domain_terms = {}

        # Should handle JSON parse error and fall back to domain extraction
        keywords = await proposal_generator.generate_keywords_with_llm(
            topic_name="Test",
            current_content="Test content",
            field_name="정의",
            topic_id="test_1",
        )

        # Should return empty list from domain extraction
        assert isinstance(keywords, list)


# =============================================================================
# Initialization Tests
# =============================================================================

class TestInitialization:
    """Test proposal generator initialization."""

    def test_initialization_without_openai(self, proposal_generator):
        """Test initialization when OpenAI is not configured."""
        # Proposal generator fixture sets client and circuit_breaker to None
        assert proposal_generator.client is None
        assert proposal_generator._circuit_breaker is None

    def test_domain_terms_loaded(self, proposal_generator):
        """Test that domain terms are loaded during initialization."""
        # Domain terms should be loaded
        assert isinstance(proposal_generator._domain_terms, dict)
        assert isinstance(proposal_generator._compound_terms, dict)

    def test_stopwords_loaded(self, proposal_generator):
        """Test that stopwords are loaded during initialization."""
        # Stopwords should be loaded
        assert isinstance(proposal_generator._stopwords, set)
