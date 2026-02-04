# SPEC-KEYWORD-SIM-001: 주제 수준 의미 유사성 기반 키워드 추출

## TAG BLOCK

```
SPEC-ID: SPEC-KEYWORD-SIM-001
Title: Topic-Level Semantic Similarity Keyword Extraction
Status: Planned
Priority: High
Created: 2026-02-04
Related: SPEC-TOPIC-001, SPEC-FIX-P0
```

## 환경 (Environment)

### 시스템 컨텍스트

- **프로젝트**: ITPE Topic Enhancement System
- **백엔드**: FastAPI 기반 Python 서비스
- **임베딩 모델**: sentence-transformers/paraphrase-multilingual-MPNet-base-v2
- **벡터 DB**: ChromaDB (PersistentClient)

### 기존 구현 요약

현재 P0-KEYWORD 구현은 도메인 수준(SW, NW, DB 등)의 분류에 기반하여 키워드를 추출합니다. 이 접근 방식은 특정 도메인 내 모든 주제가 동일한 키워드 세트를 받게 되어 주제별 관련성이 떨어집니다.

**기존 API**: `GET /api/v1/keywords/suggest?domain=SW`

### 기술 제약 사항

- 임베딩 인프라는 `app/services/matching/embedding.py`에 이미 구현됨
- ChromaDB는 `app/services/matching/matcher.py`에서 이미 사용 중
- 주제 모델은 `app/db/models/topic.py`에 정의됨

## 가정 (Assumptions)

### 기술적 가정

1. 기존 임베딩 모델(sentence-transformers)이 한국어 텍스트에 대해 충분한 성능을 발휘함
2. ChromaDB 컬렉션에 참조 문서가 이미 인덱싱되어 있음
3. 키워드 임베딩은 메모리 내 캐싱을 통해 성능을 최적화할 수 있음

### 비즈니스 가정

1. 사용자는 주제와 의미적으로 관련된 키워드를 기대함
2. 도메인 수준 접근 방식보다 주제 수준 접근 방식이 사용자 만족도를 높임
3. 정확도(accuracy)가 단순 빈도 기반 접근 방식보다 중요함

## 요구사항 (Requirements)

### FR-SIM-001: 주제 콘텐츠 임베딩 생성

**WHEN** 주제 ID가 제공되면 **THEN** 시스템은 주제의 리드문, 정의, 키워드를 결합하여 임베딩을 생성해야 한다.

- 리드문, 정의, 키워드 필드를 결합하여 텍스트를 구성
- 기존 `EmbeddingService`의 `encode_async` 메서드를 재사용
- 임베딩 결과는 캐싱하여 반복 계산 방지

### FR-SIM-002: 참조 문서 키워드 추출

**WHEN** 참조 문서가 인덱싱될 때 **THEN** 시스템은 각 문서에서 키워드를 추출하고 임베딩을 생성해야 한다.

- `KeywordExtractor`를 사용하여 참조 문서에서 키워드 추출
- 각 키워드에 대한 임베딩 생성
- 키워드-임베딩 쌍을 검색 가능한 형태로 저장

### FR-SIM-003: 의미 유사성 계산

**WHEN** 주제 임베딩과 키워드 임베딩이 준비되면 **THEN** 시스템은 코사인 유사성을 계산하고 상위 K개 결과를 반환해야 한다.

- 코사인 유사성 계산 (기존 `compute_similarity` 메서드 활용)
- 유사성 임계값 필터링 (기본값: 0.7)
- 유사성 점수로 내림차순 정렬

### FR-SIM-004: API 엔드포인트

**WHEN** 클라이언트가 `POST /api/v1/keywords/suggest-by-topic`을 요청하면 **THEN** 시스템은 주제 관련 키워드와 유사성 점수를 반환해야 한다.

**요청 본문**:
```json
{
  "topic_id": "abc-123",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**응답 본문**:
```json
{
  "keywords": [
    {"keyword": "캡슐화", "similarity": 0.92, "source": "600제_SW_120회"},
    {"keyword": "상속", "similarity": 0.89, "source": "서브노트_SW_OOP"},
    {"keyword": "다형성", "similarity": 0.87, "source": "600제_SW_125회"},
    {"keyword": "추상화", "similarity": 0.85, "source": "기출_SW_2023"}
  ]
}
```

### NFR-SIM-001: 성능

시스템은 단일 주제에 대한 키워드 추천을 500ms 이내에 처리해야 한다.

- 임베딩 캐싱으로 반복 계산 방지
- 키워드 임베딩은 사전 계산하여 메모리에 저장
- ChromaDB 쿼리 최적화

### NFR-SIM-002: 정확도

시스템은 80% 이상의 정밀도(precision)를 달성해야 한다.

- 수동 검증을 통해 관련 키워드가 상위 5개에 나타나는지 확인
- 도메인 전문가 검증 프로세스

## 명세 (Specifications)

### SP-SIM-001: 주제 텍스트 준비

주제의 리드문, 정의, 키워드 필드를 가중치와 결합하여 임베딩용 텍스트를 준비합니다.

```python
def prepare_topic_text(topic: Topic) -> str:
    """임베딩을 위한 주제 텍스트 준비."""
    parts = []
    if topic.정의:
        parts.append(topic.정의)
    if topic.리드문:
        parts.append(topic.리드문)
    if topic.키워드:
        parts.append(" ".join(topic.키워드))
    return " ".join(parts)
```

### SP-SIM-002: 키워드 임베딩 저장소

키워드 임베딩 저장소를 구현하여 빠른 유사성 검색을 지원합니다.

```python
class KeywordEmbeddingRepository:
    """키워드 임베딩 저장소."""

    def __init__(self):
        self.keywords: dict[str, np.ndarray] = {}
        self.sources: dict[str, str] = {}

    async def add_keyword(self, keyword: str, embedding: np.ndarray, source: str):
        """키워드 임베딩 추가."""
        self.keywords[keyword] = embedding
        self.sources[keyword] = source

    async def find_similar(
        self,
        topic_embedding: np.ndarray,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> list[dict]:
        """유사한 키워드 검색."""
        similarities = []
        for keyword, embedding in self.keywords.items():
            similarity = cosine_similarity(topic_embedding, embedding)
            if similarity >= threshold:
                similarities.append({
                    "keyword": keyword,
                    "similarity": float(similarity),
                    "source": self.sources[keyword]
                })
        return sorted(similarities, key=lambda x: x["similarity"], reverse=True)[:top_k]
```

### SP-SIM-003: 의미적 키워드 서비스

주제 수준 의미 유사성 기반 키워드 추천 서비스를 구현합니다.

```python
class SemanticKeywordService:
    """의미적 키워드 추천 서비스."""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.keyword_repo = KeywordEmbeddingRepository()
        self.extractor = KeywordExtractor()

    async def initialize_from_references(self):
        """참조 문서에서 키워드 추출 및 인덱싱."""
        # 참조 문서 로드 및 키워드 추출 로직
        pass

    async def suggest_keywords_by_topic(
        self,
        topic_id: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> list[dict]:
        """주제 기반 키워드 추천."""
        # 주제 로드 및 임베딩 생성
        # 유사한 키워드 검색
        pass
```

### SP-SIM-004: API 엔드포인트 구현

```python
@router.post("/suggest-by-topic", response_model=ApiResponse)
async def suggest_keywords_by_topic(
    request: KeywordByTopicRequest,
    request_id: str = Depends(get_current_request_id),
):
    """주제 기반 의미적 키워드 추천."""
    pass
```

## 추적성 (Traceability)

| 요구사항 | 명세 | 테스트 시나리오 |
|---------|------|---------------|
| FR-SIM-001 | SP-SIM-001 | ACC-SIM-001 |
| FR-SIM-002 | SP-SIM-002, SP-SIM-003 | ACC-SIM-002 |
| FR-SIM-003 | SP-SIM-002 | ACC-SIM-003 |
| FR-SIM-004 | SP-SIM-004 | ACC-SIM-004 |
| NFR-SIM-001 | - | ACC-SIM-005 |
| NFR-SIM-002 | - | ACC-SIM-006 |
