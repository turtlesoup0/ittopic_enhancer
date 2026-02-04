"""Ollama LLM client for local model inference."""

import hashlib
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.env_config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Ollama는 실제 API 키가 필요하지 않지만,
# OpenAI 클라이언트가 API 키를 요구하므로 상수로 정의합니다.
# 이 값은 인증용이 아니며, Ollama 서비스에서 무시됩니다.
OLLAMA_API_KEY_PLACEHOLDER = "ollama"


class OllamaClient:
    """Ollama client using OpenAI-compatible API."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama base URL (default from settings)
            model: Model name (default from settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

        # Ollama provides OpenAI-compatible API
        # 실제 인증용이 아니므로 상수 값을 사용합니다
        self.client = AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key=OLLAMA_API_KEY_PLACEHOLDER,
        )

        logger.info("ollama_client_initialized", base_url=self.base_url, model=self.model)

    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """
        Generate completion using Ollama.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Optional JSON format (e.g., {"type": "json_object"})

        Returns:
            Generated text content
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add response_format if specified (for JSON mode)
            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """
        Generate JSON response using Ollama.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON dictionary
        """
        import json

        # Add JSON format instruction to system message
        enhanced_messages = []
        for msg in messages:
            if msg["role"] == "system":
                enhanced_messages.append(
                    {
                        "role": "system",
                        "content": msg["content"]
                        + "\n\nIMPORTANT: Respond ONLY with valid JSON, no additional text.",
                    }
                )
            else:
                enhanced_messages.append(msg)

        try:
            response_text = await self.generate_completion(
                messages=enhanced_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse JSON response
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response from Ollama: {e}")

    async def validate_content(
        self,
        topic_title: str,
        lead: str,
        definition: str,
        keywords: list[str],
        references: list[dict],
    ) -> dict:
        """
        Validate topic content using Ollama.

        Args:
            topic_title: Topic title
            lead: Lead sentence
            definition: Definition text
            keywords: List of keywords
            references: List of reference documents

        Returns:
            Validation result dictionary with gaps and scores
        """
        # Build prompt for validation
        system_prompt = """당신은 ITPE 정보관리기술사 시험을 위한 콘텐츠 검증 전문가입니다.

제공된 토픽 내용을 검증하고 다음 Gap 유형을 식별하십시오:
1. MISSING_FIELD: 필수 필드 누락 (리드문 30자+, 정의 50자+, 키워드 3개+)
2. INCOMPLETE_DEFINITION: 정의가 기술사 수준에 미달함
3. MISSING_KEYWORDS: 필수 키워드 누락
4. OUTDATED_CONTENT: 내용이 최신 기술 동향을 반영하지 않음
5. INACCURATE_INFO: 기술적으로 부정확한 정보
6. INSUFFICIENT_DEPTH: 내용의 깊이가 부족함
7. MISSING_EXAMPLE: 실무 예시가 부족함
8. INCONSISTENT_CONTENT: 내용 간 모순이 존재

JSON 형식으로 응답하십시오:
{
  "gaps": [
    {
      "gap_type": "gap_type_name",
      "field_name": "affected_field",
      "current_value": "current_content_preview",
      "suggested_value": "improvement_suggestion",
      "confidence": 0.0-1.0,
      "reasoning": "explanation"
    }
  ],
  "overall_score": 0.0-1.0,
  "field_completeness_score": 0.0-1.0,
  "content_accuracy_score": 0.0-1.0,
  "reference_coverage_score": 0.0-1.0
}"""

        user_content = f"""토픽 제목: {topic_title}

리드문: {lead}

정의: {definition}

키워드: {", ".join(keywords) if keywords else "없음"}

참조 문서 ({len(references)}개):
"""
        for i, ref in enumerate(references[:3], 1):
            user_content += (
                f"\n{i}. {ref.get('title', 'N/A')}: {ref.get('relevant_snippet', 'N/A')[:200]}"
            )

        user_content += "\n\n위 내용을 검증하고 Gap을 식별하십시오."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            result = await self.generate_json(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            # Validate result structure
            if "gaps" not in result:
                result["gaps"] = []
            if "overall_score" not in result:
                result["overall_score"] = 0.5
            if "field_completeness_score" not in result:
                result["field_completeness_score"] = 0.5
            if "content_accuracy_score" not in result:
                result["content_accuracy_score"] = 0.5
            if "reference_coverage_score" not in result:
                result["reference_coverage_score"] = 0.5

            return result

        except Exception as e:
            logger.error(f"Ollama validation failed: {e}")
            # Return fallback result
            return {
                "gaps": [],
                "overall_score": 0.5,
                "field_completeness_score": 0.5,
                "content_accuracy_score": 0.5,
                "reference_coverage_score": 0.5,
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    @staticmethod
    def compute_reference_hash(content: str) -> str:
        """
        Compute hash for reference content caching.

        Args:
            content: Reference content

        Returns:
            SHA256 hash hex digest
        """
        return hashlib.sha256(content.encode()).hexdigest()


class LLMClientFactory:
    """Factory for creating LLM clients based on provider setting."""

    @staticmethod
    def create_client():
        """
        Create LLM client based on settings.

        Returns:
            LLM client instance (OllamaClient or AsyncOpenAI)
        """
        provider = settings.llm_provider

        if provider == "ollama":
            return OllamaClient()
        elif provider == "openai":
            from openai import AsyncOpenAI

            return AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
