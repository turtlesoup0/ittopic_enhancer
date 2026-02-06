"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.cache import CacheManager
from app.db.session import Base
from app.main import app
from app.services.parser.markdown_parser import MarkdownParser
from app.services.parser.pdf_parser import PDFParser

# asyncio mode 설정: 각 테스트가 순차적으로 실행되도록 함
# Note: pytest_asyncio is enabled via pytest.ini or setup.cfg


def pytest_configure(config):
    """Pytest 설정."""
    import sys

    # asyncio event loop policy 설정
    if sys.platform == "darwin" or sys.platform == "linux":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# Import all ORM models to ensure they're registered with Base.metadata


# =============================================================================
# Database Fixtures
# =============================================================================
@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """
    테스트용 DB 세션.

    각 테스트 함수마다 독립된 인메모리 DB를 사용합니다.
    각 테스트 후 자동으로 롤백됩니다.
    """
    # 인메모리 DB 엔진 생성
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 생성
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# =============================================================================
# Cache Fixtures
# =============================================================================
@pytest.fixture(scope="function")
async def cache_manager() -> AsyncGenerator[CacheManager]:
    """
    테스트용 캐시 매니저.

    인메모리 백엔드를 사용합니다.
    """
    cache = CacheManager()
    await cache.initialize(use_redis=False)

    yield cache

    await cache.close()


@pytest.fixture(scope="function")
async def redis_cache_manager() -> AsyncGenerator[CacheManager]:
    """
    테스트용 Redis 캐시 매니저.

    Redis가 사용 가능한 경우에만 작동합니다.
    """
    cache = CacheManager()
    try:
        await cache.initialize(use_redis=True)
        if cache.backend == "redis":
            yield cache
        else:
            pytest.skip("Redis not available")
    except Exception:
        pytest.skip("Redis connection failed")
    finally:
        await cache.close()


# =============================================================================
# HTTP Client Fixtures
# =============================================================================
@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient]:
    """
    테스트용 비동기 HTTP 클라이언트.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def clean_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """
    Integration 테스트용 비동기 HTTP 클라이언트.

    인메모리 DB를 사용하며, 각 테스트 후 자동으로 정리됩니다.
    db_session fixture에 의존하여 테스트 격리을 보장합니다.
    """
    import uuid

    from httpx import ASGITransport

    # 고유한 API 키 생성 (테스트마다 다른 값)
    TEST_API_KEY = f"test-api-key-{uuid.uuid4()}"

    # DB 세션 오버라이드 - override the dependency that routes actually use
    async def override_get_db():
        yield db_session

    # 의존성 오버라이드 - routes use app.api.deps.get_db
    from app.api.deps import get_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        # API 키 헤더와 함께 클라이언트 생성
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": TEST_API_KEY},
        ) as client:
            yield client
    finally:
        # 오버라이드 정리
        app.dependency_overrides.clear()
        await db_session.rollback()


# =============================================================================
# Repository Fixtures
# =============================================================================
@pytest.fixture
def topic_repo(db_session: AsyncSession):
    """TopicRepository fixture."""
    from app.db.repositories.topic import TopicRepository

    return TopicRepository(db_session)


@pytest.fixture
def validation_repo(db_session: AsyncSession):
    """ValidationRepository fixture."""
    from app.db.repositories.validation import ValidationRepository

    return ValidationRepository(db_session)


@pytest.fixture
def validation_task_repo(db_session: AsyncSession):
    """ValidationTaskRepository fixture."""
    from app.db.repositories.validation import ValidationTaskRepository

    return ValidationTaskRepository(db_session)


@pytest.fixture
def reference_repo(db_session: AsyncSession):
    """ReferenceRepository fixture."""
    from app.db.repositories.reference import ReferenceRepository

    return ReferenceRepository(db_session)


@pytest.fixture
def proposal_repo(db_session: AsyncSession):
    """ProposalRepository fixture."""
    from app.db.repositories.proposal import ProposalRepository

    return ProposalRepository(db_session)


# =============================================================================
# Model Fixtures
# =============================================================================
@pytest.fixture
def sample_topic_create():
    """샘플 TopicCreate fixture."""
    from app.models.topic import DomainEnum, TopicCreate

    return TopicCreate(
        file_path="/test/path/topic1.md",
        file_name="topic1.md",
        folder="test_folder",
        domain=DomainEnum.SW,
        리드문="테스트 리드문",
        정의="테스트 정의",
        키워드=["키워드1", "키워드2"],
        해시태그="#테스트",
        암기="테스트 암기",
    )


@pytest.fixture
def sample_reference_create():
    """샘플 ReferenceCreate fixture."""
    from app.models.reference import ReferenceCreate, ReferenceSourceType
    from app.models.topic import DomainEnum

    return ReferenceCreate(
        source_type=ReferenceSourceType.PDF_BOOK,
        title="테스트 참조 문서",
        content="테스트 참조 문서 내용입니다.",
        url="https://example.com/test",
        file_path="/test/path/reference.pdf",
        domain=DomainEnum.SW.value,
        trust_score=1.0,
    )


@pytest.fixture
def sample_validation_result():
    """샘플 ValidationResult fixture."""
    import uuid
    from datetime import datetime

    from app.models.reference import ReferenceSourceType
    from app.models.validation import ContentGap, GapType, MatchedReference, ValidationResult

    return ValidationResult(
        id=str(uuid.uuid4()),
        topic_id="test_topic_1",
        overall_score=0.85,
        field_completeness_score=0.9,
        content_accuracy_score=0.8,
        reference_coverage_score=0.85,
        gaps=[
            ContentGap(
                gap_type=GapType.INCOMPLETE_DEFINITION,
                field_name="정의",
                current_value="현재 정의 내용",
                suggested_value="제안된 정의 내용",
                confidence=0.9,
                reference_id="ref_1",
                reasoning="정의가 부족합니다",
            ),
        ],
        matched_references=[
            MatchedReference(
                reference_id="ref_1",
                title="관련 참조 문서",
                source_type=ReferenceSourceType.PDF_BOOK,
                similarity_score=0.9,
                domain="SW",
                trust_score=1.0,
                relevant_snippet="관련 내용",
            ),
        ],
        validation_timestamp=datetime.now(),
    )


@pytest.fixture
def sample_proposal():
    """샘플 EnhancementProposal fixture."""
    import uuid
    from datetime import datetime

    from app.models.proposal import EnhancementProposal, ProposalPriority

    return EnhancementProposal(
        id=str(uuid.uuid4()),
        topic_id="test_topic_1",
        priority=ProposalPriority.HIGH,
        title="정의 내용 강화 제안",
        description="현재 정의 내용을 보강합니다",
        current_content="현재 정의",
        suggested_content="제안된 정의",
        reasoning="정의가 불충분함",
        reference_sources=["ref_1"],
        estimated_effort=30,  # 분 단위 정수
        confidence=0.9,
        created_at=datetime.now(),
    )


# =============================================================================
# Legacy Fixtures
# =============================================================================
@pytest.fixture
def pdf_parser():
    """PDFParser 인스턴스 fixture."""
    return PDFParser()


@pytest.fixture
def markdown_parser():
    """MarkdownParser 인스턴스 fixture."""
    return MarkdownParser()


@pytest.fixture
def sample_pdf_path(tmp_path):
    """테스트용 PDF 파일 fixture."""
    pdf_path = tmp_path / "test_sample.pdf"
    return str(pdf_path)


@pytest.fixture
def fb21_base_path():
    """FB21 수험 서적 기본 경로."""
    return Path(
        "/Users/turtlesoup0-macmini/Library/CloudStorage/MYBOX-sjco1/공유 폴더/공유받은 폴더/FB21기 수업자료"
    )


@pytest.fixture
def fb21_sample_files(fb21_base_path):
    """FB21 샘플 PDF 파일 목록."""
    if not fb21_base_path.exists():
        pytest.skip("FB21 경로에 접근할 수 없습니다")
        return []

    first_folder = next(fb21_base_path.glob("0*"), None)
    if not first_folder:
        return []

    pdf_files = list(first_folder.glob("*.pdf"))[:3]
    return [str(f) for f in pdf_files]


@pytest.fixture
def domain_mapping():
    """기술사 도메인 매핑 fixture."""
    return {
        "SW": ["소프트웨어 공학", "요구사항 명세"],
        "정보보안": ["정보보안", "보안 정책"],
        "신기술": ["인공지능", "딥러닝"],
        "네트워크": ["네트워크", "OSI 7계층"],
        "데이터베이스": ["데이터베이스", "SQL"],
    }
