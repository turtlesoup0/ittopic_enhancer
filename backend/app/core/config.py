"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional, Union, List
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "ITPE Topic Enhancement"
    app_version: str = "1.0.0"
    debug: bool = False

    # API
    api_prefix: str = "/api/v1"
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/itpe-enhancement.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Cache
    cache_enabled: bool = True
    cache_backend: str = "redis"  # redis or memory
    cache_ttl_embedding: int = 604800  # 7 days (seconds)
    cache_ttl_validation: int = 3600  # 1 hour (seconds)
    cache_ttl_llm: int = 86400  # 24 hours (seconds)

    # ChromaDB
    chromadb_path: str = "./data/chromadb"
    chromadb_collection: str = "references"

    # Obsidian
    obsidian_vault_path: str = ""
    obsidian_export_path: str = ""

    # Reference Sources
    fb21_books_path: str = ""
    # blog_skby_url: str = "https://blog.skby.net"  # Deferred to future enhancement

    # Embedding
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MPNet-base-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_dimension: int = 768

    # Matching - Similarity Thresholds
    similarity_threshold: float = 0.7
    similarity_threshold_pdf_book: float = 0.65
    similarity_threshold_blog: float = 0.6
    similarity_threshold_markdown: float = 0.7
    top_k_references: int = 5

    # Matching - Field Weights for Embedding
    field_weight_definition: float = 0.35
    field_weight_lead: float = 0.25
    field_weight_keywords: float = 0.25
    field_weight_hashtags: float = 0.10
    field_weight_memory: float = 0.05

    # Matching - Trust Score Integration
    trust_score_pdf_book: float = 1.0
    trust_score_blog: float = 0.8
    trust_score_markdown: float = 0.6
    trust_score_weight: float = 0.3  # Weight for trust_score in final_score
    base_similarity_weight: float = 0.7  # Base weight for similarity_score

    # Matching - Document Chunking
    chunk_size_threshold: int = 5000
    chunk_overlap: int = 500

    # LLM
    llm_provider: str = "openai"  # openai or ollama
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1000

    # Validation
    validation_rules_path: str = "./config/validation_rules.yaml"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
