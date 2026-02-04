# SPEC-KEYWORD-SIM-001: 구현 계획

## TAG BLOCK

```
SPEC-ID: SPEC-KEYWORD-SIM-001
Document: plan.md
Version: 1.0
Created: 2026-02-04
```

## 우선순위별 마일스톤

### 1차 목표 (Primary Goal): 핵심 기능 구현

- [ ] 키워드 임베딩 저장소 구현
- [ ] 주제 텍스트 준비 및 임베딩 생성
- [ ] 의미 유사성 계산 서비스 구현
- [ ] API 엔드포인트 구현
- [ ] 단위 테스트 작성

### 2차 목표 (Secondary Goal): 성능 최적화

- [ ] 임베딩 캐싱 구현
- [ ] 키워드 사전 인덱싱
- [ ] 성능 벤치마크 및 튜닝

### 3차 목표 (Final Goal): 검증 및 문서화

- [ ] 정확도 검증
- [ ] API 문서화
- [ ] 통합 테스트

## 기술 접근 방식

### 아키텍처 설계

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                 │
│  POST /api/v1/keywords/suggest-by-topic                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                               │
│  SemanticKeywordService                                      │
│  - suggest_keywords_by_topic()                               │
│  - initialize_from_references()                              │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│  KeywordEmbeddingRepo    │    │  EmbeddingService           │
│  - keywords (dict)       │    │  (Existing)                 │
│  - sources (dict)        │    │  - encode_async()           │
│  - find_similar()        │    │  - compute_similarity()     │
└──────────────────────────┘    └─────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer                                  │
│  TopicORM                                                   │
│  ReferenceDocumentORM                                       │
└─────────────────────────────────────────────────────────────┘
```

### 기존 구현 재사용

1. **EmbeddingService** (`app/services/matching/embedding.py`)
   - `encode_async()`: 텍스트 임베딩 생성
   - `compute_similarity()`: 코사인 유사성 계산
   - 기존 캐싱 인프라 활용

2. **KeywordExtractor** (`app/services/matching/keyword_extractor.py`)
   - 참조 문서에서 키워드 추출
   - 복합어 보존 및 불용어 필터링

3. **Topic/Reference 모델** (`app/models/topic.py`, `app/models/reference.py`)
   - 주제 및 참조 문서 데이터 구조

### 새로운 컴포넌트

1. **KeywordEmbeddingRepository**
   - 키워드 임베딩 저장소 (인메모리)
   - 빠른 유사성 검색을 위한 인덱싱

2. **SemanticKeywordService**
   - 주제 기반 키워드 추천 핵심 로직
   - 참조 문서에서 키워드 추출 및 인덱싱

3. **API 엔드포인트**
   - `POST /api/v1/keywords/suggest-by-topic`

## 구현 단계

### Phase 1: 기반 구조 구축

**파일 생성**:
- `app/services/matching/semantic_keywords.py`
- `app/api/v1/endpoints/semantic_keywords.py`

**핵심 클래스**:
```python
# app/services/matching/semantic_keywords.py

class KeywordEmbeddingRepository:
    """키워드 임베딩 저장소."""

    def __init__(self):
        self._keywords: dict[str, np.ndarray] = {}
        self._sources: dict[str, str] = {}
        self._embedding_service = get_embedding_service()

    async def add_keyword(self, keyword: str, embedding: np.ndarray, source: str):
        """키워드 임베딩 추가."""

    async def find_similar(
        self, topic_embedding: np.ndarray, top_k: int, threshold: float
    ) -> list[KeywordSuggestion]:
        """유사한 키워드 검색."""


class SemanticKeywordService:
    """의미적 키워드 추천 서비스."""

    def __init__(self):
        self._repo = KeywordEmbeddingRepository()
        self._embedding_service = get_embedding_service()
        self._extractor = KeywordExtractor()
        self._initialized = False

    async def initialize_from_references(self):
        """참조 문서에서 키워드 추출 및 인덱싱."""

    async def suggest_keywords_by_topic(
        self, topic_id: str, top_k: int, threshold: float
    ) -> list[KeywordSuggestion]:
        """주제 기반 키워드 추천."""
```

### Phase 2: API 엔드포인트 구현

**Pydantic 모델**:
```python
# app/models/semantic_keywords.py

from pydantic import BaseModel, Field

class KeywordByTopicRequest(BaseModel):
    """주제 기반 키워드 추천 요청."""
    topic_id: str = Field(..., description="주제 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="반환할 키워드 수")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="유사성 임계값"
    )

class KeywordSuggestion(BaseModel):
    """키워드 추천 결과."""
    keyword: str
    similarity: float
    source: str
```

**엔드포인트**:
```python
# app/api/v1/endpoints/semantic_keywords.py

@router.post("/suggest-by-topic", response_model=ApiResponse)
async def suggest_keywords_by_topic(
    request: KeywordByTopicRequest,
    request_id: str = Depends(get_current_request_id),
):
    """주제 기반 의미적 키워드 추천."""
    pass
```

### Phase 3: 초기화 프로세스

애플리케이션 시작 시 참조 문서에서 키워드를 추출하고 인덱싱:

```python
# app/api/v1/endpoints/semantic_keywords.py

_semantic_service: SemanticKeywordService | None = None

async def get_semantic_service() -> SemanticKeywordService:
    """의미적 키워드 서비스 인스턴스 반환."""
    global _semantic_service
    if _semantic_service is None:
        _semantic_service = SemanticKeywordService()
        await _semantic_service.initialize_from_references()
    return _semantic_service

# 애플리케이션 시작 시 초기화 (lifespan 이벤트)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리."""
    # 시동 시 키워드 인덱싱
    service = await get_semantic_service()
    logger.info(f"semantic_keywords_initialized: {len(service._repo._keywords)} keywords")
    yield
    # 종료 시 정리
    await _semantic_service.cleanup()
```

## 위험 요소 및 대응 계획

### 위험 1: 성능 저하

**위험**: 키워드 수가 많을 경우 유사성 계산이 느려질 수 있음

**대응**:
- 키워드 임베딩을 사전 계산하여 캐싱
- ChromaDB에 키워드 컬렉션을 추가하여 벡터 검색 가속화
- 최대 키워드 수 제한 (상위 1000개)

### 위험 2: 메모리 사용량

**위험**: 모든 키워드 임베딩을 메모리에 저장할 경우 메모리 사용량 증가

**대응**:
- 키워드 수 제한 (빈도 기반 상위 N개)
- 필요시 ChromaDB 영구 저장소 활용
- LRU 캐싱 전략

### 위험 3: 정확도 검증 어려움

**위험**: 정성적 평가가 필요하여 자동화가 어려움

**대응**:
- 도메인 전문가 수동 검증 프로세스
- 테스트 케이스에 기대 결과 포함
- A/B 테스트를 통해 기존 방식과 비교

## 의존성

### 내부 의존성

- `app/services/matching/embedding.py` - 임베딩 서비스
- `app/services/matching/keyword_extractor.py` - 키워드 추출기
- `app/models/topic.py` - 주제 모델
- `app/models/reference.py` - 참조 문서 모델
- `app/db/repositories/topic.py` - 주제 리포지토리

### 외부 의존성

- `sentence-transformers` - 임베딩 모델 (이미 사용 중)
- `numpy` - 배열 연산 (이미 사용 중)
- `chromadb` - 벡터 DB (이미 사용 중)

## 테스트 전략

### 단위 테스트

- `KeywordEmbeddingRepository`: 키워드 추가, 검색 테스트
- `SemanticKeywordService`: 주제 기반 추천 테스트
- Mock 임베딩으로 테스트 격리

### 통합 테스트

- API 엔드포인트 테스트
- 실제 참조 문서로 초기화 테스트
- 성능 벤치마크 (500ms 목표)

### 정확도 검증

- 도메인 전문가 수동 검증
- 기대 결과와 비교하는 테스트 케이스
