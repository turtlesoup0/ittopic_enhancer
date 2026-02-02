"""
통합 캐시 매니저.

서비스별 캐싱 전략을 제공하는 통합 캐시 시스템입니다.
- 캐시 키 포맷: {service}:{entity_id}:{content_hash}
- 서비스별 TTL 설정
- 무효화 트리거 지원
- Redis/인메모리 백엔드 추상화
"""
import json
import hashlib
from typing import Optional, Dict, Any, List, Set
from datetime import timedelta
from dataclasses import dataclass, field
from collections import OrderedDict

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

try:
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None


# =============================================================================
# 캐시 TTL 설정 (서비스별)
# =============================================================================
@dataclass
class CacheTTL:
    """서비스별 TTL 설정."""

    # 임베딩: 7일 (콘텐츠 변경 시 무효화)
    EMBEDDING: int = int(timedelta(days=7).total_seconds())

    # 검증 결과: 1시간 (토픽/참조 변경 시 무효화)
    VALIDATION: int = int(timedelta(hours=1).total_seconds())

    # LLM 응답: 24시간 (프롬프트 변경 시 무효화)
    LLM_RESPONSE: int = int(timedelta(hours=24).total_seconds())

    # 기본 TTL
    DEFAULT: int = int(timedelta(hours=1).total_seconds())


# =============================================================================
# 인메모리 캐시 백엔드 (Fallback)
# =============================================================================
class InMemoryCache:
    """인메모리 캐시 백엔드 (Redis fallback)."""

    def __init__(self, max_size: int = 1000):
        """
        인메모리 캐시 초기화.

        Args:
            max_size: 최대 캐시 항목 수
        """
        self._cache: OrderedDict[str, tuple[str, int]] = OrderedDict()
        self._max_size = max_size

    def _make_space(self):
        """공간이 부족하면 가장 오래된 항목 제거 (LRU)."""
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

    async def get(self, key: str) -> Optional[str]:
        """
        캐시에서 값을 가져옵니다.

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        if key in self._cache:
            value, ttl = self._cache[key]
            # TTL 확인
            import time
            if ttl > int(time.time()):
                # LRU 업데이트 (가장 최근으로 이동)
                self._cache.move_to_end(key)
                return value
            else:
                # 만료된 항목 제거
                del self._cache[key]
        return None

    async def set(self, key: str, value: str, ttl: int):
        """
        캐시에 값을 저장합니다.

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초)
        """
        self._make_space()

        import time
        expiry = int(time.time()) + ttl
        self._cache[key] = (value, expiry)
        self._cache.move_to_end(key)

    async def delete(self, *keys: str):
        """
        캐시 항목을 삭제합니다.

        Args:
            keys: 삭제할 키들
        """
        for key in keys:
            self._cache.pop(key, None)

    async def scan_iter(self, match: str) -> List[str]:
        """
        패턴과 일치하는 키를 찾습니다.

        Args:
            match: 매칭 패턴 (예: "service:*")

        Returns:
            일치하는 키 목록
        """
        import fnmatch
        matched = []
        for key in self._cache.keys():
            if fnmatch.fnmatch(key, match):
                matched.append(key)
        return matched

    async def flushdb(self):
        """모든 캐시를 비웁니다."""
        self._cache.clear()


# =============================================================================
# 통합 캐시 매니저
# =============================================================================
class CacheManager:
    """
    통합 캐시 매니저.

    서비스별 캐싱 전략을 제공하는 통합 캐시 시스템입니다.
    - 캐시 키 포맷: {service}:{entity_id}:{content_hash}
    - 서비스별 TTL 설정
    - 무효화 트리거 지원
    - Redis/인메모리 백엔드 추상화
    """

    # 서비스 타입 정의
    SERVICE_EMBEDDING = "embedding"
    SERVICE_VALIDATION = "validation"
    SERVICE_LLM = "llm"

    def __init__(self):
        """캐시 매니저를 초기화합니다."""
        self._redis: Optional[Redis] = None
        self._in_memory: Optional[InMemoryCache] = None
        self._backend: str = "none"  # "redis", "memory", "none"
        self._enabled = False
        self._ttl = CacheTTL()

    async def initialize(self, use_redis: bool = True):
        """
        캐시 백엔드를 초기화합니다.

        Args:
            use_redis: Redis 사용 여부 (False면 인메모리 사용)
        """
        # Redis 우선 시도
        if use_redis and REDIS_AVAILABLE:
            try:
                self._redis = Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
                await self._redis.ping()
                self._backend = "redis"
                self._enabled = True
                logger.info("cache_redis_initialized", url=settings.redis_url)
                return
            except Exception as e:
                logger.warning("cache_redis_init_failed", error=str(e))

        # 인메모리 fallback
        self._in_memory = InMemoryCache(max_size=1000)
        self._backend = "memory"
        self._enabled = True
        logger.info("cache_memory_initialized")

    async def close(self):
        """캐시 연결을 닫습니다."""
        if self._redis:
            await self._redis.close()
        if self._in_memory:
            await self._in_memory.flushdb()
        self._enabled = False
        logger.info("cache_closed")

    # -------------------------------------------------------------------------
    # 캐시 키 생성
    # -------------------------------------------------------------------------
    @staticmethod
    def _compute_hash(content: str) -> str:
        """
        콘텐츠 해시를 계산합니다.

        Args:
            content: 해싱할 콘텐츠

        Returns:
            SHA256 해시 (앞 16자)
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def make_key(
        self,
        service: str,
        entity_id: str,
        content: str,
    ) -> str:
        """
        캐시 키를 생성합니다.

        포맷: {service}:{entity_id}:{content_hash}

        Args:
            service: 서비스 타입 (embedding, validation, llm)
            entity_id: 엔티티 ID (topic_id, reference_id 등)
            content: 콘텐츠 (해싱용)

        Returns:
            캐시 키
        """
        content_hash = self._compute_hash(content)
        return f"{service}:{entity_id}:{content_hash}"

    def make_key_multiple(
        self,
        service: str,
        entity_id: str,
        contents: List[str],
    ) -> str:
        """
        여러 콘텐츠의 복합 해시로 캐시 키를 생성합니다.

        Args:
            service: 서비스 타입
            entity_id: 엔티티 ID
            contents: 콘텐츠 목록

        Returns:
            캐시 키
        """
        combined = "|".join(sorted(contents))
        content_hash = self._compute_hash(combined)
        return f"{service}:{entity_id}:{content_hash}"

    # -------------------------------------------------------------------------
    # 기본 CRUD 연산
    # -------------------------------------------------------------------------
    def _get_ttl_for_service(self, service: str) -> int:
        """서비스별 TTL을 반환합니다."""
        ttl_map = {
            self.SERVICE_EMBEDDING: self._ttl.EMBEDDING,
            self.SERVICE_VALIDATION: self._ttl.VALIDATION,
            self.SERVICE_LLM: self._ttl.LLM_RESPONSE,
        }
        return ttl_map.get(service, self._ttl.DEFAULT)

    async def get(
        self,
        service: str,
        entity_id: str,
        content: str,
    ) -> Optional[Dict[str, Any]]:
        """
        캐시에서 값을 가져옵니다.

        Args:
            service: 서비스 타입
            entity_id: 엔티티 ID
            content: 콘텐츠 (키 생성용)

        Returns:
            캐시된 값 또는 None
        """
        if not self._enabled:
            return None

        try:
            key = self.make_key(service, entity_id, content)
            cached = None

            if self._backend == "redis" and self._redis:
                cached = await self._redis.get(key)
            elif self._backend == "memory" and self._in_memory:
                cached = await self._in_memory.get(key)

            if cached:
                logger.debug("cache_hit", key=key, service=service)
                return json.loads(cached)

            logger.debug("cache_miss", key=key, service=service)
            return None

        except Exception as e:
            logger.warning("cache_get_failed", error=str(e), service=service)
            return None

    async def set(
        self,
        service: str,
        entity_id: str,
        content: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        캐시에 값을 저장합니다.

        Args:
            service: 서비스 타입
            entity_id: 엔티티 ID
            content: 콘텐츠 (키 생성용)
            value: 저장할 값
            ttl: TTL (초), None이면 서비스 기본값 사용
        """
        if not self._enabled:
            return

        try:
            key = self.make_key(service, entity_id, content)
            ttl = ttl or self._get_ttl_for_service(service)

            if self._backend == "redis" and self._redis:
                await self._redis.setex(
                    key,
                    ttl,
                    json.dumps(value, ensure_ascii=False),
                )
            elif self._backend == "memory" and self._in_memory:
                await self._in_memory.set(
                    key,
                    json.dumps(value, ensure_ascii=False),
                    ttl,
                )

            logger.debug("cache_set", key=key, service=service, ttl=ttl)

        except Exception as e:
            logger.warning("cache_set_failed", error=str(e), service=service)

    async def delete(self, *keys: str):
        """
        캐시 항목을 삭제합니다.

        Args:
            keys: 삭제할 키들
        """
        if not self._enabled:
            return

        try:
            if self._backend == "redis" and self._redis:
                await self._redis.delete(*keys)
            elif self._backend == "memory" and self._in_memory:
                await self._in_memory.delete(*keys)

            logger.debug("cache_deleted", count=len(keys))

        except Exception as e:
            logger.warning("cache_delete_failed", error=str(e))

    # -------------------------------------------------------------------------
    # 무효화 트리거
    # -------------------------------------------------------------------------
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """
        패턴으로 캐시를 무효화합니다.

        Args:
            pattern: 무효화 패턴 (예: "validation:topic-123:*")

        Returns:
            무효화된 항목 수
        """
        if not self._enabled:
            return 0

        try:
            keys = []

            if self._backend == "redis" and self._redis:
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)

            elif self._backend == "memory" and self._in_memory:
                keys = await self._in_memory.scan_iter(pattern)
                if keys:
                    await self._in_memory.delete(*keys)

            count = len(keys)
            if count > 0:
                logger.info("cache_invalidated", pattern=pattern, count=count)

            return count

        except Exception as e:
            logger.warning("cache_invalidate_failed", error=str(e), pattern=pattern)
            return 0

    async def invalidate_topic(self, topic_id: str) -> int:
        """
        토픽 관련 모든 캐시를 무효화합니다.

        - 임베딩 캐시 무효화
        - 검증 캐시 무효화
        - LLM 캐시 무효화

        Args:
            topic_id: 토픽 ID

        Returns:
            무효화된 항목 수
        """
        patterns = [
            f"{self.SERVICE_EMBEDDING}:{topic_id}:*",
            f"{self.SERVICE_VALIDATION}:{topic_id}:*",
            f"{self.SERVICE_LLM}:{topic_id}:*",
        ]

        total = 0
        for pattern in patterns:
            total += await self.invalidate_by_pattern(pattern)

        logger.info("cache_topic_invalidated", topic_id=topic_id, total=total)
        return total

    async def invalidate_reference(self, reference_id: str) -> int:
        """
        참조 문서 관련 모든 캐시를 무효화합니다.

        - 해당 참조를 사용하는 검증 캐시 무효화

        Args:
            reference_id: 참조 문서 ID

        Returns:
            무효화된 항목 수
        """
        # 참조 문서가 포함된 검증 결과는 참조 내용이 변경되면 무효화
        # (실제 구현에서는 참조 ID를 캐시 키에 포함해야 함)
        pattern = f"{self.SERVICE_VALIDATION}:*:{reference_id}*"

        count = await self.invalidate_by_pattern(pattern)
        logger.info("cache_reference_invalidated", reference_id=reference_id, count=count)
        return count

    async def flush_all(self) -> int:
        """
        모든 캐시를 비웁니다 (설정 변경 시).

        Returns:
            무효화된 항목 수
        """
        patterns = [
            f"{self.SERVICE_EMBEDDING}:*",
            f"{self.SERVICE_VALIDATION}:*",
            f"{self.SERVICE_LLM}:*",
        ]

        total = 0
        for pattern in patterns:
            total += await self.invalidate_by_pattern(pattern)

        logger.info("cache_flushed_all", total=total)
        return total

    # -------------------------------------------------------------------------
    # 캐스케이딩 무효화 (연관된 캐시 함께 무효화)
    # -------------------------------------------------------------------------
    async def invalidate_on_topic_update(self, topic_id: str) -> int:
        """
        토픽 수정 시 캐스케이딩 무효화.

        Args:
            topic_id: 수정된 토픽 ID

        Returns:
            무효화된 총 항목 수
        """
        return await self.invalidate_topic(topic_id)

    async def invalidate_on_reference_update(self, reference_id: str, affected_topics: Optional[List[str]] = None) -> int:
        """
        참조 문서 수정 시 캐스케이딩 무효화.

        Args:
            reference_id: 수정된 참조 문서 ID
            affected_topics: 영향받는 토픽 ID 목록 (선택)

        Returns:
            무효화된 총 항목 수
        """
        total = await self.invalidate_reference(reference_id)

        # 영향받는 토픽이 지정되면 해당 토픽의 캐시도 무효화
        if affected_topics:
            for topic_id in affected_topics:
                total += await self.invalidate_topic(topic_id)

        return total

    async def invalidate_on_settings_change(self) -> int:
        """
        설정 변경 시 전체 캐시 플러시.

        Returns:
            무효화된 총 항목 수
        """
        return await self.flush_all()

    # -------------------------------------------------------------------------
    # 상태 확인
    # -------------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        """캐시 활성화 여부."""
        return self._enabled

    @property
    def backend(self) -> str:
        """사용 중인 백엔드 (redis, memory, none)."""
        return self._backend

    def get_ttl_config(self) -> Dict[str, int]:
        """
        TTL 설정을 반환합니다.

        Returns:
            서비스별 TTL 설정 (초 단위)
        """
        return {
            self.SERVICE_EMBEDDING: self._ttl.EMBEDDING,
            self.SERVICE_VALIDATION: self._ttl.VALIDATION,
            self.SERVICE_LLM: self._ttl.LLM_RESPONSE,
        }


# =============================================================================
# 전역 캐시 매니저 인스턴스
# =============================================================================
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """
    전역 캐시 매니저 인스턴스를 반환합니다.

    Returns:
        CacheManager 인스턴스
    """
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()

    return _cache_manager
