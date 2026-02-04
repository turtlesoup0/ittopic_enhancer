"""
중앙화된 환경변수 설정 모듈

보안 규칙:
- 모든 환경변수는 get_settings()를 통해서만 접근해야 합니다
- 직접 import os; os.environ.get() 사용을 금지합니다
- 환경변수 유효성 검사와 기본값을 중앙에서 관리합니다
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvConfigError(Exception):
    """필수 환경변수가 누락된 경우 발생하는 에러"""

    def __init__(self, missing_keys: list[str]):
        self.missing_keys = missing_keys
        super().__init__(
            f"필수 환경변수가 누락되었습니다: {', '.join(missing_keys)}. .env 파일을 확인하세요."
        )


class Settings(BaseSettings):
    """
    애플리케이션 설정

    Pydantic Settings를 사용하여 환경변수를 로드하고 검증합니다.
    모든 환경변수는 이 클래스를 통해서만 접근해야 합니다.
    """

    # ========================================================================
    # Application Settings
    # ========================================================================
    app_name: str = "ITPE Topic Enhancement"
    app_version: str = "1.0.0"
    debug: bool = False

    # ========================================================================
    # API Settings
    # ========================================================================
    api_prefix: str = "/api/v1"
    cors_origins: list[str] | str = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        """CORS origins를 쉼표로 구분된 문자열이나 리스트에서 파싱합니다."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ========================================================================
    # Database Settings (PostgreSQL)
    # ========================================================================
    database_url: str = "sqlite+aiosqlite:///./data/itpe-enhancement.db"

    # Sync database URL for Celery workers (uses psycopg2 instead of asyncpg)
    # Celery workers cannot use async database drivers due to event loop conflicts
    sync_database_url: str | None = None

    # PostgreSQL 환경변수 (Docker Compose에서 사용)
    postgres_db: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None

    # ========================================================================
    # Redis Settings
    # ========================================================================
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str | None = None

    # ========================================================================
    # Cache Settings
    # ========================================================================
    cache_enabled: bool = True
    cache_backend: str = "redis"  # redis or memory
    cache_ttl_embedding: int = 604800  # 7 days (seconds)
    cache_ttl_validation: int = 3600  # 1 hour (seconds)
    cache_ttl_llm: int = 86400  # 24 hours (seconds)

    # ========================================================================
    # ChromaDB Settings
    # ========================================================================
    chromadb_path: str = "./data/chromadb"
    chromadb_collection: str = "references"

    # ========================================================================
    # Obsidian Settings
    # ========================================================================
    obsidian_vault_path: str = ""
    obsidian_export_path: str = ""

    # ========================================================================
    # Reference Sources Settings
    # ========================================================================
    fb21_books_path: str = ""

    # ========================================================================
    # Embedding Settings
    # ========================================================================
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MPNet-base-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_dimension: int = 768

    # ========================================================================
    # Matching Settings - Similarity Thresholds
    # ========================================================================
    similarity_threshold: float = 0.7
    similarity_threshold_pdf_book: float = 0.65
    similarity_threshold_blog: float = 0.6
    similarity_threshold_markdown: float = 0.7
    top_k_references: int = 5

    # ========================================================================
    # Matching Settings - Field Weights for Embedding
    # ========================================================================
    field_weight_definition: float = 0.35
    field_weight_lead: float = 0.25
    field_weight_keywords: float = 0.25
    field_weight_hashtags: float = 0.10
    field_weight_memory: float = 0.05

    # ========================================================================
    # Matching Settings - Trust Score Integration
    # ========================================================================
    trust_score_pdf_book: float = 1.0
    trust_score_blog: float = 0.8
    trust_score_markdown: float = 0.6
    trust_score_weight: float = 0.3
    base_similarity_weight: float = 0.7

    # ========================================================================
    # Matching Settings - Document Chunking
    # ========================================================================
    chunk_size_threshold: int = 5000
    chunk_overlap: int = 500

    # ========================================================================
    # LLM Settings
    # ========================================================================
    llm_provider: str = "openai"  # openai or ollama
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1000

    # Ollama 전용 API 키 상수 (실제 인증용이 아님)
    ollama_api_key_placeholder: str = "ollama"

    # ========================================================================
    # Validation Settings
    # ========================================================================
    validation_rules_path: str = "./config/validation_rules.yaml"

    # ========================================================================
    # Celery Settings
    # ========================================================================
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    def get_celery_broker_url(self) -> str:
        """
        비밀번호가 포함된 Celery broker URL을 반환합니다.

        Returns:
            비밀번호가 포함된 Redis URL
        """
        # URL에 이미 인증(@)이 포함되어 있는지 확인
        if "@" not in self.celery_broker_url and self.redis_password:
            # 비밀번호가 없는 경우만 추가
            return self.celery_broker_url.replace("redis://", f"redis://:{self.redis_password}@")
        return self.celery_broker_url

    def get_celery_result_backend(self) -> str:
        """
        비밀번호가 포함된 Celery result backend URL을 반환합니다.

        Returns:
            비밀번호가 포함된 Redis URL
        """
        # URL에 이미 인증(@)이 포함되어 있는지 확인
        if "@" not in self.celery_result_backend and self.redis_password:
            return self.celery_result_backend.replace(
                "redis://", f"redis://:{self.redis_password}@"
            )
        return self.celery_result_backend

    # ========================================================================
    # Security Settings
    # ========================================================================
    # API 키 헤더 이름
    api_key_header: str = "X-API-Key"
    # 허용된 API 키 목록 (SHA-256 해시로 저장 권장)
    api_keys: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_production_settings(self) -> None:
        """
        프로덕션 환경에서 필수 설정을 검증합니다.

        Raises:
            EnvConfigError: 필수 설정이 누락된 경우
        """
        if self.debug:
            # 개발 환경에서는 검증을 건너뜁니다
            return

        missing_keys = []

        # PostgreSQL 검증 (DATABASE_URL에 postgresql이 포함된 경우)
        if "postgresql" in self.database_url.lower():
            if not self.postgres_db or not self.postgres_user or not self.postgres_password:
                missing_keys.extend(["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"])

        # Redis 검증
        if self.cache_backend == "redis" or "redis" in self.redis_url.lower():
            if not self.redis_password:
                missing_keys.append("REDIS_PASSWORD")

        # LLM 제공자별 검증
        if self.llm_provider == "openai" and not self.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")

        if missing_keys:
            raise EnvConfigError(missing_keys)

    def get_redis_url_with_password(self) -> str:
        """
        비밀번호가 포함된 Redis URL을 반환합니다.

        Returns:
            비밀번호가 포함된 Redis URL
        """
        if self.redis_password and ":@" not in self.redis_url:
            # URL에 비밀번호가 없는 경우 추가
            return self.redis_url.replace("redis://", f"redis://:{self.redis_password}@")
        return self.redis_url

    def get_sync_database_url(self) -> str:
        """
        Convert async database URL to sync database URL for Celery workers.

        Converts:
        - postgresql+asyncpg://... → postgresql://...
        - sqlite+aiosqlite://... → sqlite://...

        Returns:
            Sync database URL
        """
        if self.sync_database_url:
            return self.sync_database_url

        # Auto-convert from async to sync URL
        url = self.database_url

        # PostgreSQL asyncpg → psycopg2
        if "postgresql+asyncpg://" in url:
            return url.replace("postgresql+asyncpg://", "postgresql://")

        # SQLite aiosqlite → sqlite3 (standard sqlite)
        if "sqlite+aiosqlite://" in url:
            return url.replace("sqlite+aiosqlite://", "sqlite://")

        # If no async prefix, return as-is
        return url


@lru_cache
def get_settings() -> Settings:
    """
    캐시된 설정 인스턴스를 반환합니다.

    이 함수는 애플리케이션 전체에서 설정에 접근하는 유일한 방법입니다.

    Returns:
        Settings 인스턴스
    """
    return Settings()


def validate_env() -> None:
    """
    환경변수를 검증하고 필수 값이 누락된 경우 예외를 발생시킵니다.

    애플리케이션 시작 시 호출하여 환경 설정의 올바름을 보장합니다.
    """
    settings = get_settings()
    settings.validate_production_settings()
