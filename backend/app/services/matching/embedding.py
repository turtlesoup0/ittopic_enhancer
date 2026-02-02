"""Embedding service using sentence-transformers."""
from sentence_transformers import SentenceTransformer
from typing import List, Union, Dict, Any, Optional
import numpy as np
import logging
import hashlib

from app.core.errors import EmbeddingError
from app.core.cache import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Sentence transformer-based embedding service."""

    _instance = None
    _model = None
    _cache_manager: Optional[CacheManager] = None

    def __new__(cls, model_name: str = "sentence-transformers/paraphrase-multilingual-MPNet-base-v2", device: str = "cpu"):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(model_name, device)
        return cls._instance

    async def _initialize_cache(self):
        """캐시 매니저 초기화."""
        if self._cache_manager is None:
            self._cache_manager = await get_cache_manager()

    def _initialize(self, model_name: str, device: str):
        """Initialize the embedding model."""
        try:
            logger.info(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name, device=device)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Dimension: {self._dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingError(
                message=f"Failed to initialize embedding model: {e}",
                operation="initialize",
                original_error=e,
            )

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    def _make_cache_key(self, text: str) -> str:
        """
        텍스트용 캐시 키를 생성합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            캐시 키
        """
        # 텍스트 해시 생성 (처음 100자만 사용하여 키 길이 제한)
        content_for_hash = text[:100] if len(text) > 100 else text
        content_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()[:16]
        return f"embedding:text:{content_hash}"

    async def _get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        캐시된 임베딩을 가져옵니다.

        Args:
            text: 텍스트

        Returns:
            캐시된 임베딩 또는 None
        """
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_cache_key(text)
                cached = await self._cache_manager._in_memory.get(cache_key) if self._cache_manager._in_memory else None
                if cached:
                    import json
                    data = json.loads(cached)
                    return np.array(data["embedding"])
            except Exception as e:
                logger.warning(f"Failed to get cached embedding: {e}")
        return None

    async def _cache_embedding(self, text: str, embedding: np.ndarray):
        """
        임베딩을 캐시합니다.

        Args:
            text: 텍스트
            embedding: 임베딩 벡터
        """
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_cache_key(text)
                import json
                data = {
                    "embedding": embedding.tolist(),
                    "dimension": len(embedding),
                }
                ttl = self._cache_manager._ttl.EMBEDDING
                await self._cache_manager._in_memory.set(cache_key, json.dumps(data), ttl) if self._cache_manager._in_memory else None
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {e}")

    async def invalidate_embedding_cache(self, text: str):
        """
        텍스트 관련 임베딩 캐시를 무효화합니다.

        Args:
            text: 변경된 텍스트
        """
        if self._cache_manager and self._cache_manager.enabled:
            try:
                cache_key = self._make_cache_key(text)
                await self._cache_manager._in_memory.delete(cache_key) if self._cache_manager._in_memory else None
                logger.debug(f"Invalidated embedding cache for text: {text[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to invalidate embedding cache: {e}")

    async def invalidate_all_embeddings(self):
        """모든 임베딩 캐시를 무효화합니다."""
        if self._cache_manager and self._cache_manager.enabled:
            try:
                count = await self._cache_manager.invalidate_by_pattern("embedding:text:*")
                logger.info(f"Invalidated {count} embedding caches")
            except Exception as e:
                logger.warning(f"Failed to invalidate all embeddings: {e}")

    async def encode_async(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
    ) -> Union[np.ndarray, List[float]]:
        """
        비동기로 텍스트를 임베딩 벡터로 인코딩합니다 (캐싱 지원).

        Args:
            texts: 단일 텍스트 또는 텍스트 목록
            batch_size: 배치 크기
            show_progress: 진행률 표시
            convert_to_numpy: NumPy 배열 반환

        Returns:
            임베딩 벡터(들)

        Raises:
            EmbeddingError: 인코딩 실패 시
        """
        # 캐시 초기화
        await self._initialize_cache()

        # 단일 텍스트 처리
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        # 단일 텍스트는 캐시 확인
        if single_input and self._cache_manager and self._cache_manager.enabled:
            cached = await self._get_cached_embedding(texts[0])
            if cached is not None:
                logger.debug("embedding_cache_hit")
                return cached if convert_to_numpy else cached.tolist()

        # 캐시 미스이면 인코딩 수행
        embeddings = self.encode(
            texts,
            batch_size=batch_size,
            show_progress=show_progress,
            convert_to_numpy=convert_to_numpy,
        )

        # 단일 텍스트 결과 캐싱
        if single_input and self._cache_manager and self._cache_manager.enabled:
            if convert_to_numpy:
                await self._cache_embedding(texts[0], embeddings)
            else:
                await self._cache_embedding(texts[0], np.array(embeddings))

        return embeddings

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
    ) -> Union[np.ndarray, List[float]]:
        """
        Encode text(s) to embedding vector(s).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            convert_to_numpy: Return numpy array

        Returns:
            Embedding vector(s)

        Raises:
            EmbeddingError: Encoding 실패 시
        """
        if self._model is None:
            raise EmbeddingError(
                message="Model not initialized",
                operation="encode",
            )

        # Handle single text
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        try:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=convert_to_numpy,
                normalize_embeddings=True,  # L2 normalization for cosine similarity
            )

            # Return single vector if input was single text
            if single_input and convert_to_numpy:
                return embeddings[0]
            elif single_input:
                return embeddings[0].tolist()

            return embeddings

        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise EmbeddingError(
                message=f"Failed to encode texts: {e}",
                operation="encode",
                original_error=e,
            )

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[np.ndarray]:
        """
        Encode batch of texts efficiently.

        Args:
            texts: List of texts to encode
            batch_size: Batch size

        Returns:
            List of embedding vectors
        """
        return self.encode(texts, batch_size=batch_size, show_progress=True)

    def compute_similarity(
        self,
        embedding1: Union[np.ndarray, List[float]],
        embedding2: Union[np.ndarray, List[float]],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1

        Raises:
            EmbeddingError: Similarity 계산 실패 시 (silent error return 제거)
        """
        try:
            # Convert to numpy if needed
            if not isinstance(embedding1, np.ndarray):
                embedding1 = np.array(embedding1)
            if not isinstance(embedding2, np.ndarray):
                embedding2 = np.array(embedding2)

            # Reshape if needed
            if embedding1.ndim == 1:
                embedding1 = embedding1.reshape(1, -1)
            if embedding2.ndim == 1:
                embedding2 = embedding2.reshape(1, -1)

            # Cosine similarity (embeddings are normalized)
            similarity = np.dot(embedding1, embedding2.T)[0][0]

            # Ensure result is in [0, 1]
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            # Silent error return (0.0) 제거, 명시적 에러 던지기
            raise EmbeddingError(
                message=f"Failed to compute similarity: {e}",
                operation="compute_similarity",
                original_error=e,
            )

    def compute_similarity_matrix(
        self,
        embeddings1: List[np.ndarray],
        embeddings2: List[np.ndarray],
    ) -> np.ndarray:
        """
        Compute pairwise similarity matrix.

        Args:
            embeddings1: List of embedding vectors
            embeddings2: List of embedding vectors

        Returns:
            Similarity matrix of shape (len(embeddings1), len(embeddings2))

        Raises:
            EmbeddingError: Similarity matrix 계산 실패 시
        """
        try:
            matrix1 = np.array(embeddings1)
            matrix2 = np.array(embeddings2)

            # Compute cosine similarity
            similarity = np.dot(matrix1, matrix2.T)

            return similarity

        except Exception as e:
            logger.error(f"Failed to compute similarity matrix: {e}")
            raise EmbeddingError(
                message=f"Failed to compute similarity matrix: {e}",
                operation="compute_similarity_matrix",
                original_error=e,
            )


# Global embedding service instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
