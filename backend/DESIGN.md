# ITPE Topic Enhancement - Backend Architecture Design

## Overview

This document describes the backend architecture and core algorithms for the ITPE Topic Enhancement system, focusing on the matching service that connects topics with reference documents.

---

## Matching Algorithm Specification (P0-MATCH)

### 1. Field-Weighted Embedding Strategy

#### Purpose
To improve matching quality by giving higher importance to more semantically important fields in the topic content.

#### Field Weights

| Field (Korean) | Field (English) | Weight | Rationale |
|----------------|-----------------|--------|-----------|
| 정의 | definition | 0.35 | Core concept definition is most important |
| 리드문 | lead | 0.25 | Lead paragraph provides context |
| 키워드 | keywords | 0.25 | Keywords define core concepts |
| 해시태그 | hashtags | 0.10 | Hashtags provide categorization |
| 암기 | memory | 0.05 | Memory points are supplementary |

#### Implementation

The weighted embedding is created by repeating fields according to their relative weights:

```python
# Weight Calculation: (repetitions / total_repetitions)
# 정의: 3 repetitions = 3/8 = 0.375 (~0.35)
# 리드문: 2 repetitions = 2/8 = 0.25
# 키워드: 2 repetitions = 2/8 = 0.25
# 해시태그: 1 repetition = 1/8 = 0.125 (~0.10)
# 암기: 1 repetition = 1/8 = 0.125 (~0.05)
```

**Example:**
```python
# Input topic content:
#   정의: "REST API는 HTTP 프로토콜을 기반으로 하는 웹 API 설계 아키텍처입니다."
#   리드문: "웹 서비스의 확장성과 상호운용성을 위해 설계되었습니다."
#   키워드: ["HTTP", "API", "아키텍처", "웹"]
#   해시태그: "#web #api"
#   암기: "상태 무상태성"

# Weighted text for embedding:
# "REST API는 HTTP 프로토콜을 기반으로 하는 웹 API 설계 아키텍처입니다.
#  REST API는 HTTP 프로토콜을 기반으로 하는 웹 API 설계 아키텍처입니다.
#  REST API는 HTTP 프로토콜을 기반으로 하는 웹 API 설계 아키텍처입니다.
#  웹 서비스의 확장성과 상호운용성을 위해 설계되었습니다.
#  웹 서비스의 확장성과 상호운용성을 위해 설계되었습니다.
#  HTTP API 아키텍처 웹
#  HTTP API 아키텍처 웹
#  #web #api 상태 무상태성"
```

---

### 2. Trust Score Integration

#### Purpose
To combine semantic similarity with source reliability for more accurate matching.

#### Source Trust Scores

| Source Type | Trust Score | Rationale |
|-------------|-------------|-----------|
| PDF_BOOK | 1.0 | Published books have highest reliability |
| MARKDOWN | 0.6 | Personal notes have moderate reliability |
| BLOG | 0.8 | Blog articles (future) have good reliability |

#### Final Score Formula

```
final_score = similarity_score × (base_similarity_weight + trust_score_weight × trust_score)

Where:
- similarity_score: Cosine similarity from embeddings (0-1)
- base_similarity_weight: 0.7 (minimum weight for similarity)
- trust_score_weight: 0.3 (maximum additional weight from trust)
- trust_score: Source reliability score (0-1)
```

**Examples:**

| Similarity | Trust Score | Final Score | Calculation |
|------------|-------------|-------------|-------------|
| 0.8 | 1.0 (PDF) | 0.8 × 1.0 = 0.80 | 0.8 × (0.7 + 0.3×1.0) |
| 0.8 | 0.6 (MD) | 0.8 × 0.88 = 0.70 | 0.8 × (0.7 + 0.3×0.6) |
| 0.7 | 1.0 (PDF) | 0.7 × 1.0 = 0.70 | 0.7 × (0.7 + 0.3×1.0) |
| 0.9 | 0.6 (MD) | 0.9 × 0.88 = 0.79 | 0.9 × (0.7 + 0.3×0.6) |

#### Implementation
```python
def _compute_final_score(self, similarity_score: float, trust_score: float) -> float:
    trust_factor = settings.base_similarity_weight + settings.trust_score_weight * trust_score
    final_score = similarity_score * trust_factor
    return float(max(0.0, min(1.0, final_score)))
```

---

### 3. Source-Specific Similarity Thresholds

#### Purpose
To apply different quality thresholds based on source reliability.

#### Threshold Values

| Source Type | Threshold | Rationale |
|-------------|-----------|-----------|
| PDF_BOOK | 0.65 | Lower threshold for high-quality sources |
| MARKDOWN | 0.70 | Standard threshold for personal notes |
| BLOG | 0.60 | Lower threshold for diverse blog content |

#### Implementation
```python
SIMILARITY_THRESHOLDS = {
    ReferenceSourceType.PDF_BOOK: 0.65,
    ReferenceSourceType.MARKDOWN: 0.70,
}

def _get_similarity_threshold(self, source_type: ReferenceSourceType) -> float:
    return self.SIMILARITY_THRESHOLDS.get(source_type, 0.7)
```

---

### 4. Document Chunking Strategy

#### Purpose
To handle large documents (>5000 characters) by splitting them into manageable chunks while preserving context.

#### Chunking Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| chunk_size_threshold | 5000 | Maximum characters per chunk |
| chunk_overlap | 500 | Overlapping characters between chunks |

#### Chunking Algorithm

1. If document length <= 5000: Return as single chunk
2. Otherwise:
   - Start at position 0
   - Find end position (min(5000, document_length))
   - Look for sentence boundary (\\n\\n > \\n > . )
   - Extract chunk from start to end
   - Move start = max(start + 1, end - 500) for overlap
   - Repeat until document exhausted

#### Implementation
```python
def _chunk_document(self, content: str) -> List[str]:
    if len(content) <= settings.chunk_size_threshold:
        return [content]
    
    chunks = []
    start = 0
    content_length = len(content)
    
    while start < content_length:
        end = start + settings.chunk_size_threshold
        
        if end < content_length:
            for break_char in ['\n\n', '\n', '. ']:
                last_break = content.rfind(break_char, start, end)
                if last_break != -1 and last_break > start:
                    end = last_break + len(break_char)
                    break
        
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = max(start + 1, end - settings.chunk_overlap)
    
    return chunks
```

---

### 5. Complete Matching Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    MATCHING PIPELINE                             │
└─────────────────────────────────────────────────────────────────┘

1. TOPIC PROCESSING
   ┌─────────────────────────────────────────────────────────────┐
   │ Input: Topic with content fields                            │
   │                                                              │
   │ 1.1 Apply Field Weights:                                    │
   │     - 정의 (definition): 0.35 → 3 repetitions               │
   │     - 리드문 (lead): 0.25 → 2 repetitions                   │
   │     - 키워드 (keywords): 0.25 → 2 repetitions               │
   │     - 해시태그 (hashtags): 0.10 → 1 repetition              │
   │     - 암기 (memory): 0.05 → 1 repetition                    │
   │                                                              │
   │ 1.2 Generate Weighted Embedding                             │
   │     → topic_embedding (768-dim vector)                      │
   └─────────────────────────────────────────────────────────────┘

2. REFERENCE INDEXING (One-time)
   ┌─────────────────────────────────────────────────────────────┐
   │ Input: Reference documents                                  │
   │                                                              │
   │ 2.1 Document Chunking (if >5000 chars)                      │
   │     - Split with 500-char overlap                           │
   │     - Preserve sentence boundaries                          │
   │                                                              │
   │ 2.2 Set Default Trust Score                                 │
   │     - PDF_BOOK: 1.0                                         │
   │     - MARKDOWN: 0.6                                         │
   │                                                              │
   │ 2.3 Generate Embeddings per Chunk                           │
   │     → chunk_embedding (768-dim vector)                      │
   │                                                              │
   │ 2.4 Store in ChromaDB                                       │
   │     - id: {ref_id}_chunk{N}                                 │
   │     - metadata: {source_type, trust_score, domain, ...}     │
   └─────────────────────────────────────────────────────────────┘

3. SIMILARITY SEARCH
   ┌─────────────────────────────────────────────────────────────┐
   │ 3.1 Query ChromaDB                                          │
   │     - query_embeddings: [topic_embedding]                   │
   │     - n_results: top_k × 3 (get more for filtering)         │
   │     - where: domain filter (optional)                       │
   │                                                              │
   │ 3.2 Process Results                                         │
   │     For each result:                                         │
│     a. Calculate raw similarity: 1 - cosine_distance          │
   │     b. Get trust_score from metadata                        │
   │     c. Compute final_score:                                 │
   │        similarity × (0.7 + 0.3 × trust_score)               │
   │     d. Apply source-specific threshold                      │
   │     e. Deduplicate chunks by parent_id                      │
   │                                                              │
   │ 3.3 Sort by final_score (descending)                        │
   │ 3.4 Return top_k results                                    │
   └─────────────────────────────────────────────────────────────┘

OUTPUT: MatchedReference[]
        - reference_id
        - title
        - source_type
        - similarity_score (final adjusted score)
        - trust_score
        - relevant_snippet
```

---

## Configuration

All matching-related configuration is centralized in `app/core/config.py`:

```python
# Matching - Similarity Thresholds
similarity_threshold: float = 0.7                    # Default fallback
similarity_threshold_pdf_book: float = 0.65
similarity_threshold_blog: float = 0.6
similarity_threshold_markdown: float = 0.7

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
trust_score_weight: float = 0.3
base_similarity_weight: float = 0.7

# Matching - Document Chunking
chunk_size_threshold: int = 5000
chunk_overlap: int = 500
```

---

## Testing Strategy

### Unit Tests
- Test field weight calculation
- Test trust score integration formula
- Test document chunking with various sizes
- Test threshold selection by source type

### Integration Tests
- Test end-to-end matching pipeline
- Test ChromaDB integration with chunks
- Test similarity search with domain filtering

### Performance Tests
- Benchmark embedding generation with weights
- Measure query latency with different top_k values
- Test chunking impact on index size

---

## Future Enhancements

1. **Dynamic Weight Learning**: Learn optimal field weights from user feedback
2. **Cross-Lingual Matching**: Support Korean-English cross-language matching
3. **Temporal Decay**: Reduce trust score for outdated references
4. **User Personalization**: Adjust weights based on user preferences
5. **Query Expansion**: Expand topic queries with related terms

---

## References

- ChromaDB Documentation: https://docs.trychroma.com/
- Sentence Transformers: https://www.sbert.net/
- Cosine Similarity: Standard metric for embedding comparison
