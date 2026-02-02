"""Ollama LLM client for local model inference."""
from openai import AsyncOpenAI
from typing import Optional, Dict, Any
import logging
import hashlib

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Ollama client using OpenAI-compatible API."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama base URL (default from settings)
            model: Model name (default from settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

        # Ollama provides OpenAI-compatible API
        self.client = AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama",  # Ollama doesn't require real API key
        )

        logger.info(f"Ollama client initialized: {self.base_url}, model={self.model}")

    async def generate_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
        response_format: Optional[Dict[str, str]] = None,
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
        messages: list[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
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
                enhanced_messages.append({
                    "role": "system",
                    "content": msg["content"] + "\n\nIMPORTANT: Respond ONLY with valid JSON, no additional text.",
                })
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
