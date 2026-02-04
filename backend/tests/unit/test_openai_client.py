"""Unit tests for OpenAI LLM client."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.llm.openai import LLMClientFactory, OpenAIClient

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response content"
    return mock_response


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI client."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def mock_openai_json_response():
    """Mock OpenAI API response with JSON content."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"key": "value"}'
    return mock_response


@pytest.fixture
def openai_client_with_mock(mock_openai_client):
    """OpenAIClient with mocked AsyncOpenAI client."""
    with patch("app.services.llm.openai.AsyncOpenAI", return_value=mock_openai_client):
        client = OpenAIClient(api_key="test-api-key")
        client.client = mock_openai_client
        return client


# =============================================================================
# Initialization Tests
# =============================================================================


class TestOpenAIClientInitialization:
    """Test OpenAI client initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch("app.services.llm.openai.AsyncOpenAI") as mock_openai:
            client = OpenAIClient(api_key="test-api-key")

            assert client.api_key == "test-api-key"
            assert client.client is not None
            mock_openai.assert_called_once()

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch("app.services.llm.openai.settings") as mock_settings:
            mock_settings.openai_api_key = None
            with patch("app.services.llm.openai.AsyncOpenAI") as mock_openai:
                client = OpenAIClient()

                assert client.api_key is None
                assert client.client is None
                mock_openai.assert_not_called()

    def test_init_uses_settings_defaults(self):
        """Test that initialization uses settings defaults."""
        with patch("app.services.llm.openai.settings") as mock_settings:
            mock_settings.openai_api_key = "settings-api-key"
            mock_settings.openai_model = "gpt-4"
            with patch("app.services.llm.openai.AsyncOpenAI") as mock_openai:
                client = OpenAIClient()

                assert client.api_key == "settings-api-key"
                assert client.model == "gpt-4"


# =============================================================================
# Generate Completion Tests
# =============================================================================


class TestGenerateCompletion:
    """Test generate_completion method."""

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, openai_client_with_mock, mock_openai_response):
        """Test successful completion generation."""
        openai_client_with_mock.client.chat.completions.create.return_value = mock_openai_response

        messages = [{"role": "user", "content": "Test message"}]
        result = await openai_client_with_mock.generate_completion(messages)

        assert result == "Test response content"
        openai_client_with_mock.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_completion_with_temperature(
        self, openai_client_with_mock, mock_openai_response
    ):
        """Test completion generation with custom temperature."""
        openai_client_with_mock.client.chat.completions.create.return_value = mock_openai_response

        messages = [{"role": "user", "content": "Test"}]
        result = await openai_client_with_mock.generate_completion(
            messages, temperature=0.7, max_tokens=500
        )

        assert result == "Test response content"
        call_kwargs = openai_client_with_mock.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_generate_completion_with_response_format(
        self, openai_client_with_mock, mock_openai_response
    ):
        """Test completion generation with JSON response format."""
        openai_client_with_mock.client.chat.completions.create.return_value = mock_openai_response

        messages = [{"role": "user", "content": "Test"}]
        result = await openai_client_with_mock.generate_completion(
            messages, response_format={"type": "json_object"}
        )

        assert result == "Test response content"
        call_kwargs = openai_client_with_mock.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_generate_completion_no_client(self):
        """Test completion generation fails without client."""
        client = OpenAIClient(api_key=None)

        with pytest.raises(RuntimeError, match="not initialized"):
            await client.generate_completion([{"role": "user", "content": "Test"}])


# =============================================================================
# Generate JSON Tests
# =============================================================================


class TestGenerateJson:
    """Test generate_json method."""

    @pytest.mark.asyncio
    async def test_generate_json_success(self, openai_client_with_mock):
        """Test successful JSON generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"key": "value", "number": 123}'
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        result = await openai_client_with_mock.generate_json(messages)

        assert result == {"key": "value", "number": 123}

    @pytest.mark.asyncio
    async def test_generate_json_invalid_json(self, openai_client_with_mock):
        """Test JSON generation with invalid JSON response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(ValueError, match="Invalid JSON response"):
            await openai_client_with_mock.generate_json(messages)


# =============================================================================
# Validate Content Tests (P0 Critical)
# =============================================================================


class TestValidateContent:
    """Test validate_content method - critical for P0."""

    @pytest.mark.asyncio
    async def test_validate_content_success(self, openai_client_with_mock):
        """Test successful content validation."""
        # Mock JSON response
        validation_result = {
            "gaps": [
                {
                    "gap_type": "MISSING_KEYWORDS",
                    "field_name": "키워드",
                    "current_value": "AI",
                    "suggested_value": "AI, Machine Learning, Neural Network",
                    "confidence": 0.85,
                    "reasoning": "핵심 키워드가 부족합니다",
                }
            ],
            "overall_score": 0.75,
            "field_completeness_score": 0.8,
            "content_accuracy_score": 0.7,
            "reference_coverage_score": 0.75,
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(validation_result)
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await openai_client_with_mock.validate_content(
            topic_title="인공지능",
            lead="AI 기술 소개",
            definition="기계가 지능을 구현",
            keywords=["AI"],
            references=[{"title": "AI 개론", "relevant_snippet": "AI는 인공지능입니다"}],
        )

        assert result["overall_score"] == 0.75
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["gap_type"] == "MISSING_KEYWORDS"

    @pytest.mark.asyncio
    async def test_validate_content_no_gaps(self, openai_client_with_mock):
        """Test validation with no gaps detected."""
        validation_result = {
            "gaps": [],
            "overall_score": 0.95,
            "field_completeness_score": 0.95,
            "content_accuracy_score": 0.95,
            "reference_coverage_score": 0.95,
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(validation_result)
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await openai_client_with_mock.validate_content(
            topic_title="완벽한 토픽",
            lead="완벽한 리드문입니다",
            definition="완벽한 정의입니다",
            keywords=["키워드1", "키워드2", "키워드3"],
            references=[],
        )

        assert result["overall_score"] == 0.95
        assert len(result["gaps"]) == 0

    @pytest.mark.asyncio
    async def test_validate_content_incomplete_response(self, openai_client_with_mock):
        """Test validation with incomplete JSON response."""
        # Response missing some required fields
        incomplete_result = {"gaps": [{"gap_type": "MISSING_FIELD", "field_name": "리드문"}]}

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(incomplete_result)
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await openai_client_with_mock.validate_content(
            topic_title="테스트",
            lead="테스트",
            definition="테스트",
            keywords=[],
            references=[],
        )

        # Should add default values for missing fields
        assert "overall_score" in result
        assert "field_completeness_score" in result
        assert result["overall_score"] == 0.5

    @pytest.mark.asyncio
    async def test_validate_content_error_fallback(self, openai_client_with_mock):
        """Test validation fallback on error."""
        openai_client_with_mock.client.chat.completions.create.side_effect = Exception("API Error")

        result = await openai_client_with_mock.validate_content(
            topic_title="테스트",
            lead="테스트",
            definition="테스트",
            keywords=[],
            references=[],
        )

        # Should return fallback result
        assert result["overall_score"] == 0.5
        assert "error" in result

    @pytest.mark.asyncio
    async def test_validate_content_no_client(self):
        """Test validation fails without client."""
        client = OpenAIClient(api_key=None)

        with pytest.raises(RuntimeError, match="not initialized"):
            await client.validate_content(
                topic_title="테스트",
                lead="테스트",
                definition="테스트",
                keywords=[],
                references=[],
            )


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, openai_client_with_mock):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await openai_client_with_mock.health_check()

        assert result is True
        openai_client_with_mock.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_no_client(self):
        """Test health check without client."""
        client = OpenAIClient(api_key=None)

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_api_error(self, openai_client_with_mock):
        """Test health check with API error."""
        openai_client_with_mock.client.chat.completions.create.side_effect = Exception("API Error")

        result = await openai_client_with_mock.health_check()

        assert result is False


# =============================================================================
# LLMClientFactory Tests
# =============================================================================


class TestLLMClientFactory:
    """Test LLM client factory."""

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        with patch("app.services.llm.openai.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            with patch("app.services.llm.openai.OpenAIClient") as mock_openai:
                client = LLMClientFactory.create_client()

                mock_openai.assert_called_once()

    def test_create_ollama_client(self):
        """Test creating Ollama client."""
        with patch("app.services.llm.openai.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            with patch("app.services.llm.ollama_client.OllamaClient") as mock_ollama:
                client = LLMClientFactory.create_client()

                mock_ollama.assert_called_once()

    def test_create_unsupported_provider(self):
        """Test creating client with unsupported provider."""
        with patch("app.services.llm.openai.settings") as mock_settings:
            mock_settings.llm_provider = "unsupported"

            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                LLMClientFactory.create_client()


# =============================================================================
# Korean Language Tests
# =============================================================================


class TestKoreanLanguage:
    """Korean language support tests."""

    @pytest.mark.asyncio
    async def test_validate_korean_content(self, openai_client_with_mock):
        """Test validation with Korean content."""
        validation_result = {
            "gaps": [
                {
                    "gap_type": "INCOMPLETE_DEFINITION",
                    "field_name": "정의",
                    "current_value": "짧음",
                    "suggested_value": "상세한 정의",
                    "confidence": 0.9,
                    "reasoning": "정의가 불충분합니다",
                }
            ],
            "overall_score": 0.7,
            "field_completeness_score": 0.7,
            "content_accuracy_score": 0.7,
            "reference_coverage_score": 0.7,
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(validation_result)
        openai_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await openai_client_with_mock.validate_content(
            topic_title="데이터베이스",
            lead="데이터를 저장하는 시스템",
            definition="데이터베이스는 구조화된 데이터 집합입니다",
            keywords=["DB", "SQL"],
            references=[],
        )

        assert result["overall_score"] == 0.7
        assert len(result["gaps"]) == 1
