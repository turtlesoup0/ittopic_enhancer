"""Unit tests for Ollama LLM client."""

import hashlib
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.llm.ollama_client import OLLAMA_API_KEY_PLACEHOLDER, OllamaClient

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response content"
    return mock_response


@pytest.fixture
def mock_async_openai_client():
    """Mock AsyncOpenAI client for Ollama."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def ollama_client_with_mock(mock_async_openai_client):
    """OllamaClient with mocked AsyncOpenAI client."""
    with patch("app.services.llm.ollama_client.AsyncOpenAI", return_value=mock_async_openai_client):
        client = OllamaClient(base_url="http://localhost:11434")
        client.client = mock_async_openai_client
        return client


# =============================================================================
# Initialization Tests
# =============================================================================


class TestOllamaClientInitialization:
    """Test Ollama client initialization."""

    def test_init_with_base_url(self):
        """Test initialization with custom base URL."""
        with patch("app.services.llm.ollama_client.AsyncOpenAI") as mock_openai:
            client = OllamaClient(base_url="http://localhost:11434")

            assert client.base_url == "http://localhost:11434"
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args.kwargs
            assert call_kwargs["base_url"] == "http://localhost:11434/v1"
            assert call_kwargs["api_key"] == OLLAMA_API_KEY_PLACEHOLDER

    def test_init_uses_settings_defaults(self):
        """Test that initialization uses settings defaults."""
        with patch("app.services.llm.ollama_client.settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434"
            mock_settings.ollama_model = "llama3.2"
            with patch("app.services.llm.ollama_client.AsyncOpenAI") as mock_openai:
                client = OllamaClient()

                assert client.base_url == "http://localhost:11434"
                assert client.model == "llama3.2"


# =============================================================================
# Generate Completion Tests
# =============================================================================


class TestGenerateCompletion:
    """Test generate_completion method."""

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, ollama_client_with_mock, mock_ollama_response):
        """Test successful completion generation."""
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_ollama_response

        messages = [{"role": "user", "content": "Test message"}]
        result = await ollama_client_with_mock.generate_completion(messages)

        assert result == "Test response content"
        ollama_client_with_mock.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_completion_with_temperature(
        self, ollama_client_with_mock, mock_ollama_response
    ):
        """Test completion generation with custom temperature."""
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_ollama_response

        messages = [{"role": "user", "content": "Test"}]
        result = await ollama_client_with_mock.generate_completion(
            messages, temperature=0.7, max_tokens=500
        )

        assert result == "Test response content"
        call_kwargs = ollama_client_with_mock.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_generate_completion_error_handling(self, ollama_client_with_mock):
        """Test completion generation error handling."""
        ollama_client_with_mock.client.chat.completions.create.side_effect = Exception(
            "Ollama Error"
        )

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception, match="Ollama Error"):
            await ollama_client_with_mock.generate_completion(messages)


# =============================================================================
# Generate JSON Tests
# =============================================================================


class TestGenerateJson:
    """Test generate_json method."""

    @pytest.mark.asyncio
    async def test_generate_json_success(self, ollama_client_with_mock):
        """Test successful JSON generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"key": "value", "number": 123}'
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        result = await ollama_client_with_mock.generate_json(messages)

        assert result == {"key": "value", "number": 123}

    @pytest.mark.asyncio
    async def test_generate_json_enhances_system_message(self, ollama_client_with_mock):
        """Test that generate_json adds JSON instruction to system message."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"result": "success"}'
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Test"},
        ]

        await ollama_client_with_mock.generate_json(messages)

        # Check that system message was enhanced
        call_kwargs = ollama_client_with_mock.client.chat.completions.create.call_args.kwargs
        enhanced_system_msg = call_kwargs["messages"][0]
        assert (
            "enhanced_system_msg" in locals()
            or "IMPORTANT: Respond ONLY with valid JSON" in str(call_kwargs["messages"])
        )

    @pytest.mark.asyncio
    async def test_generate_json_invalid_json(self, ollama_client_with_mock):
        """Test JSON generation with invalid JSON response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(ValueError, match="Invalid JSON response"):
            await ollama_client_with_mock.generate_json(messages)


# =============================================================================
# Validate Content Tests
# =============================================================================


class TestValidateContent:
    """Test validate_content method."""

    @pytest.mark.asyncio
    async def test_validate_content_success(self, ollama_client_with_mock):
        """Test successful content validation."""
        # Mock JSON response
        validation_result = {
            "gaps": [
                {
                    "gap_type": "MISSING_KEYWORDS",
                    "field_name": "키워드",
                    "current_value": "AI",
                    "suggested_value": "AI, Machine Learning, Deep Learning",
                    "confidence": 0.9,
                    "reasoning": "핵심 키워드가 부족합니다",
                }
            ],
            "overall_score": 0.8,
            "field_completeness_score": 0.85,
            "content_accuracy_score": 0.8,
            "reference_coverage_score": 0.75,
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(validation_result)
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await ollama_client_with_mock.validate_content(
            topic_title="인공지능",
            lead="AI 기술 설명",
            definition="기계가 인간 지능을 모방하는 기술",
            keywords=["AI"],
            references=[{"title": "AI 개론", "relevant_snippet": "AI는 인공지능입니다"}],
        )

        assert result["overall_score"] == 0.8
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["gap_type"] == "MISSING_KEYWORDS"

    @pytest.mark.asyncio
    async def test_validate_content_incomplete_response(self, ollama_client_with_mock):
        """Test validation with incomplete JSON response."""
        incomplete_result = {"gaps": [{"gap_type": "MISSING_FIELD", "field_name": "리드문"}]}

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(incomplete_result)
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await ollama_client_with_mock.validate_content(
            topic_title="테스트",
            lead="테스트",
            definition="테스트",
            keywords=[],
            references=[],
        )

        # Should add default values for missing fields
        assert "overall_score" in result
        assert result["overall_score"] == 0.5

    @pytest.mark.asyncio
    async def test_validate_content_error_fallback(self, ollama_client_with_mock):
        """Test validation fallback on error."""
        ollama_client_with_mock.client.chat.completions.create.side_effect = Exception(
            "Ollama Error"
        )

        result = await ollama_client_with_mock.validate_content(
            topic_title="테스트",
            lead="테스트",
            definition="테스트",
            keywords=[],
            references=[],
        )

        # Should return fallback result
        assert result["overall_score"] == 0.5
        assert "error" in result


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = OllamaClient(base_url="http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with failure."""
        client = OllamaClient(base_url="http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Test health check with exception."""
        client = OllamaClient(base_url="http://localhost:11434")

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__.raise_exception = Exception("Connection error")

            result = await client.health_check()

            assert result is False


# =============================================================================
# Compute Reference Hash Tests
# =============================================================================


class TestComputeReferenceHash:
    """Test compute_reference_hash static method."""

    def test_compute_hash_same_content(self):
        """Test hash is consistent for same content."""
        content = "Test reference content"

        hash1 = OllamaClient.compute_reference_hash(content)
        hash2 = OllamaClient.compute_reference_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_compute_hash_different_content(self):
        """Test hash is different for different content."""
        hash1 = OllamaClient.compute_reference_hash("content 1")
        hash2 = OllamaClient.compute_reference_hash("content 2")

        assert hash1 != hash2

    def test_compute_hash_matches_sha256(self):
        """Test hash matches standard SHA256."""
        content = "Test content"

        computed_hash = OllamaClient.compute_reference_hash(content)
        expected_hash = hashlib.sha256(content.encode()).hexdigest()

        assert computed_hash == expected_hash

    def test_compute_hash_unicode_content(self):
        """Test hash works with Unicode/Korean content."""
        content = "한글 테스트 내용"

        hash1 = OllamaClient.compute_reference_hash(content)
        hash2 = OllamaClient.compute_reference_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64


# =============================================================================
# Korean Language Tests
# =============================================================================


class TestKoreanLanguage:
    """Korean language support tests."""

    @pytest.mark.asyncio
    async def test_validate_korean_content(self, ollama_client_with_mock):
        """Test validation with Korean content."""
        validation_result = {
            "gaps": [
                {
                    "gap_type": "INCOMPLETE_DEFINITION",
                    "field_name": "정의",
                    "current_value": "짧음",
                    "suggested_value": "상세한 정의 필요",
                    "confidence": 0.85,
                    "reasoning": "정의가 기술사 수준에 미달",
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
        ollama_client_with_mock.client.chat.completions.create.return_value = mock_response

        result = await ollama_client_with_mock.validate_content(
            topic_title="데이터베이스",
            lead="데이터를 관리하는 시스템",
            definition="구조화된 데이터 집합과 관리 시스템",
            keywords=["DB", "SQL", "RDBMS"],
            references=[],
        )

        assert result["overall_score"] == 0.7
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["field_name"] == "정의"
