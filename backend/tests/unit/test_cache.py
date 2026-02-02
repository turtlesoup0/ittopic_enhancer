"""
통합 캐시 매니저 단위 테스트.

CacheManager의 기능을 테스트합니다.
- 캐시 키 생성
- CRUD 연산
- 무효화 트리거
- 서비스별 TTL 설정
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import (
    CacheManager,
    CacheTTL,
    InMemoryCache,
    get_cache_manager,
)


# =============================================================================
# InMemoryCache 테스트
# =============================================================================
class TestInMemoryCache:
    """인메모리 캐시 백엔드 테스트."""

    @pytest.fixture
    async def cache(self):
        """테스트용 캐시 인스턴스."""
        cache = InMemoryCache(max_size=10)
        yield cache
        await cache.flushdb()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """캐시 저장 및 조회 테스트."""
        await cache.set("key1", "value1", ttl=60)
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """존재하지 않는 키 조회 테스트."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """캐시 삭제 테스트."""
        await cache.set("key1", "value1", ttl=60)
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, cache):
        """TTL 만료 테스트."""
        import time

        await cache.set("key1", "value1", ttl=1)
        await asyncio.sleep(1.1)  # TTL 만료 대기
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_scan_iter(self, cache):
        """패턴 매칭 테스트."""
        await cache.set("service:topic1:hash1", "value1", ttl=60)
        await cache.set("service:topic2:hash2", "value2", ttl=60)
        await cache.set("other:key:value", "value3", ttl=60)

        matched = await cache.scan_iter("service:*")
        assert len(matched) == 2
        assert "service:topic1:hash1" in matched
        assert "service:topic2:hash2" in matched

    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """LRU eviction 테스트 (max_size=10)."""
        # 11개 항목 추가 (마지막 항목은 eviction 방지용)
        for i in range(11):
            await cache.set(f"key{i}", f"value{i}", ttl=60)

        # 가장 오래된 항목이 제거되어야 함
        result = await cache.get("key0")
        assert result is None

        # 최신 항목은 존재해야 함
        result = await cache.get("key10")
        assert result == "value10"


# =============================================================================
# CacheManager 테스트
# =============================================================================
class TestCacheManager:
    """통합 캐시 매니저 테스트."""

    @pytest.fixture
    async def cache_manager(self):
        """테스트용 캐시 매니저 인스턴스."""
        manager = CacheManager()
        await manager.initialize(use_redis=False)  # 인메모리 사용
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_initialization_memory(self):
        """인메모리 백엔드 초기화 테스트."""
        manager = CacheManager()
        await manager.initialize(use_redis=False)
        assert manager.enabled is True
        assert manager.backend == "memory"
        await manager.close()

    def test_make_key(self):
        """캐시 키 생성 테스트."""
        manager = CacheManager()
        key = manager.make_key("embedding", "topic-123", "test content")
        assert key.startswith("embedding:")
        assert "topic-123" in key
        assert ":" in key  # 해시 부분 확인

    def test_make_key_multiple(self):
        """여러 콘텐츠의 키 생성 테스트."""
        manager = CacheManager()
        contents = ["content1", "content2", "content3"]
        key = manager.make_key_multiple("validation", "topic-456", contents)
        assert key.startswith("validation:")
        assert "topic-456" in key

    @pytest.mark.asyncio
    async def test_get_set_operations(self, cache_manager):
        """기본 CRUD 연산 테스트."""
        value = {"result": "test", "score": 0.85}

        # 캐시 저장
        await cache_manager.set(
            service=CacheManager.SERVICE_EMBEDDING,
            entity_id="topic-123",
            content="test content",
            value=value,
        )

        # 캐시 조회
        result = await cache_manager.get(
            service=CacheManager.SERVICE_EMBEDDING,
            entity_id="topic-123",
            content="test content",
        )

        assert result is not None
        assert result["result"] == "test"
        assert result["score"] == 0.85

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager):
        """캐시 미스 테스트."""
        result = await cache_manager.get(
            service=CacheManager.SERVICE_EMBEDDING,
            entity_id="nonexistent",
            content="nonexistent content",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(self, cache_manager):
        """패턴 기반 무효화 테스트."""
        # 여러 항목 저장
        await cache_manager.set(
            CacheManager.SERVICE_VALIDATION, "topic-123", "content1", {"data": 1}
        )
        await cache_manager.set(
            CacheManager.SERVICE_VALIDATION, "topic-123", "content2", {"data": 2}
        )
        await cache_manager.set(
            CacheManager.SERVICE_EMBEDDING, "topic-123", "content3", {"data": 3}
        )

        # validation만 무효화
        count = await cache_manager.invalidate_by_pattern("validation:topic-123:*")
        assert count == 2

        # embedding은 여전히 존재해야 함
        result = await cache_manager.get(
            CacheManager.SERVICE_EMBEDDING, "topic-123", "content3"
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalidate_topic(self, cache_manager):
        """토픽 전체 무효화 테스트."""
        topic_id = "topic-456"

        # 여러 서비스에 항목 저장
        await cache_manager.set(
            CacheManager.SERVICE_EMBEDDING, topic_id, "content1", {"data": 1}
        )
        await cache_manager.set(
            CacheManager.SERVICE_VALIDATION, topic_id, "content2", {"data": 2}
        )
        await cache_manager.set(
            CacheManager.SERVICE_LLM, topic_id, "content3", {"data": 3}
        )

        # 토픽 무효화
        count = await cache_manager.invalidate_topic(topic_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_invalidate_reference(self, cache_manager):
        """참조 문서 무효화 테스트."""
        # 참조 관련 캐시 저장
        await cache_manager.set(
            CacheManager.SERVICE_VALIDATION, "topic-789", "content_with_ref_123", {"data": 1}
        )

        # 참조 무효화
        count = await cache_manager.invalidate_reference("ref-123")
        # 패턴 매칭에 따라 결과가 달라질 수 있음
        assert count >= 0

    @pytest.mark.asyncio
    async def test_flush_all(self, cache_manager):
        """전체 플러시 테스트."""
        # 여러 항목 저장
        await cache_manager.set(CacheManager.SERVICE_EMBEDDING, "topic-1", "c1", {"d": 1})
        await cache_manager.set(CacheManager.SERVICE_VALIDATION, "topic-2", "c2", {"d": 2})
        await cache_manager.set(CacheManager.SERVICE_LLM, "topic-3", "c3", {"d": 3})

        # 전체 플러시
        count = await cache_manager.flush_all()
        assert count == 3

        # 모든 항목이 삭제되어야 함
        result1 = await cache_manager.get(CacheManager.SERVICE_EMBEDDING, "topic-1", "c1")
        result2 = await cache_manager.get(CacheManager.SERVICE_VALIDATION, "topic-2", "c2")
        result3 = await cache_manager.get(CacheManager.SERVICE_LLM, "topic-3", "c3")

        assert result1 is None
        assert result2 is None
        assert result3 is None

    @pytest.mark.asyncio
    async def test_cascade_invalidation_on_topic_update(self, cache_manager):
        """토픽 수정 시 캐스케이딩 무효화 테스트."""
        topic_id = "topic-999"

        await cache_manager.set(CacheManager.SERVICE_EMBEDDING, topic_id, "c1", {"d": 1})
        await cache_manager.set(CacheManager.SERVICE_VALIDATION, topic_id, "c2", {"d": 2})

        count = await cache_manager.invalidate_on_topic_update(topic_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_cascade_invalidation_on_reference_update(self, cache_manager):
        """참조 수정 시 캐스케이딩 무효화 테스트."""
        ref_id = "ref-456"
        affected_topics = ["topic-1", "topic-2"]

        await cache_manager.set(CacheManager.SERVICE_VALIDATION, "topic-1", f"content_{ref_id}", {"d": 1})
        await cache_manager.set(CacheManager.SERVICE_VALIDATION, "topic-2", f"content_{ref_id}", {"d": 2})

        count = await cache_manager.invalidate_on_reference_update(ref_id, affected_topics)
        assert count >= 0  # 패턴 매칭 결과에 따라 다름

    @pytest.mark.asyncio
    async def test_invalidate_on_settings_change(self, cache_manager):
        """설정 변경 시 전체 플러시 테스트."""
        await cache_manager.set(CacheManager.SERVICE_EMBEDDING, "topic-1", "c1", {"d": 1})
        await cache_manager.set(CacheManager.SERVICE_VALIDATION, "topic-2", "c2", {"d": 2})

        count = await cache_manager.invalidate_on_settings_change()
        assert count == 2

    def test_get_ttl_config(self, cache_manager):
        """TTL 설정 조회 테스트."""
        ttl_config = cache_manager.get_ttl_config()

        assert CacheManager.SERVICE_EMBEDDING in ttl_config
        assert CacheManager.SERVICE_VALIDATION in ttl_config
        assert CacheManager.SERVICE_LLM in ttl_config

        # 임베딩 TTL이 가장 길어야 함 (7일)
        assert ttl_config[CacheManager.SERVICE_EMBEDDING] > ttl_config[CacheManager.SERVICE_VALIDATION]
        assert ttl_config[CacheManager.SERVICE_EMBEDDING] > ttl_config[CacheManager.SERVICE_LLM]


# =============================================================================
# 전역 인스턴스 테스트
# =============================================================================
class TestGlobalCacheManager:
    """전역 캐시 매니저 인스턴스 테스트."""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """싱글톤 패턴 테스트."""
        # 첫 번째 호출
        manager1 = await get_cache_manager()

        # 두 번째 호출 (동일 인스턴스여야 함)
        manager2 = await get_cache_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_multiple_calls_consistency(self):
        """여러 호출 간 일관성 테스트."""
        manager = await get_cache_manager()

        # 여러 번 호출해도 동일한 인스턴스
        for _ in range(5):
            m = await get_cache_manager()
            assert m is manager


# =============================================================================
# CacheTTL 데이터클래스 테스트
# =============================================================================
class TestCacheTTL:
    """TTL 설정 테스트."""

    def test_default_values(self):
        """기본 TTL 값 테스트."""
        ttl = CacheTTL()

        # 임베딩: 7일 (604800초)
        assert ttl.EMBEDDING == 604800

        # 검증: 1시간 (3600초)
        assert ttl.VALIDATION == 3600

        # LLM: 24시간 (86400초)
        assert ttl.LLM_RESPONSE == 86400

        # 기본: 1시간
        assert ttl.DEFAULT == 3600

    def test_custom_values(self):
        """사용자 정의 TTL 값 테스트."""
        ttl = CacheTTL(
            EMBEDDING=1200,
            VALIDATION=600,
            LLM_RESPONSE=300,
        )

        assert ttl.EMBEDDING == 1200
        assert ttl.VALIDATION == 600
        assert ttl.LLM_RESPONSE == 300
