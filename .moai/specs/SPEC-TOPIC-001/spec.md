# SPEC-TOPIC-001: ITPE Topic Enhancement System

---

## TAG BLOCK

```
TAG: SPEC-TOPIC-001
Title: ITPE Topic Enhancement System - Core Specification
Status: Implementation
Priority: High
Created: 2026-02-02
Completed: 2026-02-02
Domain: Backend, Frontend, AI/ML
Related: SPEC-REVIEW-001
Implementation Report: DDD_IMPLEMENTATION_REPORT.md
```

---

## 1. Environment

### 1.1 System Context

**Target System:** ITPE Topic Enhancement System

**Purpose:** Information Technology Professional Engineer (ITPE) exam preparation automation system that validates Obsidian study notes against FB21 textbooks and blog references, then generates enhancement proposals from technical expert perspective.

**Stakeholders:**
- Primary: ITPE exam candidates using Obsidian for study management
- Secondary: Technical content validators and proposal reviewers

**System Boundaries:**
- **IN:** Obsidian Dataview JSON export, FB21 PDF textbooks, blog references
- **OUT:** Validation results, enhancement proposals, progress metrics
- **External Dependencies:** OpenAI API (or Ollama), ChromaDB, SentenceTransformers model

### 1.2 Assumptions

**Technical Assumptions:**
- [HIGH] Obsidian vault accessible at specified local path
- [HIGH] FB21 textbook files available in PDF format
- [MEDIUM] SentenceTransformers multilingual model supports Korean embeddings
- [MEDIUM] ChromaDB persistent storage maintains vector indices across restarts
- [LOW] OpenAI API maintains current pricing (~$0.0075 per topic)

**Business Assumptions:**
- [HIGH] Users have basic Obsidian and Dataview plugin knowledge
- [MEDIUM] ITPE exam content structure remains consistent across exam cycles
- [MEDIUM] "Technical Expert Perspective" validation rules can be codified
- [LOW] User acceptance rate > 70% for generated proposals

**Integration Assumptions:**
- [HIGH] Local LLM (Ollama) can substitute for OpenAI API during outages
- [MEDIUM] Blog content extraction complies with robots.txt and rate limits

---

## 2. Requirements (EARS Format)

### 2.1 Functional Requirements

#### FR-001: Topic Data Extraction
**WHEN** user exports Obsidian topics via Dataview JSON, **THE SYSTEM SHALL** parse and validate topic structure including metadata (file_path, file_name, folder, domain) and content fields (리드문, 정의, 키워드, 해시태그, 암기).

#### FR-002: Reference Document Processing
**WHEN** reference documents (PDF books, blog posts, markdown files) are provided, **THE SYSTEM SHALL** extract text content, generate embeddings using SentenceTransformers multilingual-MPNet-base-v2, and index in ChromaDB with domain and source_type metadata.

#### FR-003: Semantic Topic-Reference Matching
**WHEN** a topic requires validation, **THE SYSTEM SHALL** find top-k similar references using cosine similarity search on ChromaDB with configurable threshold (default 0.7), applying field-weighted embedding strategy and trust_score adjustment.

#### FR-004: Content Validation
**WHEN** topics and matched references are compared, **THE SYSTEM SHALL** detect content gaps including MISSING_FIELD, INCOMPLETE_DEFINITION, MISSING_KEYWORDS, INSUFFICIENT_DEPTH, MISSING_EXAMPLE, and INCONSISTENT_CONTENT using semantic comparison against validation rules.

#### FR-005: Enhancement Proposal Generation
**WHEN** validation gaps are identified, **THE SYSTEM SHALL** generate enhancement proposals with priority (CRITICAL, HIGH, MEDIUM, LOW), suggested_content, reasoning, and estimated_effort using LLM for CRITICAL/HIGH gaps and template-based generation for MEDIUM/LOW gaps.

#### FR-006: Keyword Suggestion
**WHEN** keyword gap is detected, **THE SYSTEM SHALL** extract domain-specific technical terms from matched references using LLM or frequency-based extraction, preserving compound terms (e.g., "TCP/IP", "REST API") and filtering by domain vocabulary.

#### FR-007: Validation Result Storage
**WHEN** validation completes, **THE SYSTEM SHALL** persist ValidationResult, ContentGap, and EnhancementProposal in SQLite with proper relationships, caching LLM responses by (topic_id, gap_type, reference_hash) with 24-hour TTL.

#### FR-008: API Response Delivery
**WHEN** client requests validation status, **THE SYSTEM SHALL** return task progress via polling endpoint with current/total counts, or completed results with overall_score, gaps array, and matched_references list.

### 2.2 Non-Functional Requirements

#### NFR-001: Performance - Topic Matching
**THE SYSTEM SHALL** complete single topic matching operation within 5 seconds including embedding generation, vector search, and reference ranking.

**THE SYSTEM SHALL** complete batch validation of 100 topics within 10 minutes using concurrent processing with Celery workers.

#### NFR-002: Performance - API Response
**THE SYSTEM SHALL** respond to 95th percentile of read-only API requests (GET endpoints) within 200ms after warm-up, measured excluding external LLM API latency.

#### NFR-003: Availability - Graceful Degradation
**WHEN** LLM service is unavailable, **THE SYSTEM SHALL** degrade to template-based proposal generation with reduced quality but continued operation, logging the fallback event with timestamp and reason.

**WHEN** ChromaDB query fails, **THE SYSTEM SHALL** fall back to TF-IDF based search using TopicSearchService with degraded matching quality.

#### NFR-004: Security - API Authentication
**THE SYSTEM SHALL** require API key authentication for all POST/PUT/DELETE endpoints using X-API-Key header, validating against stored keys with SHA-256 hashing.

#### NFR-005: Security - Rate Limiting
**THE SYSTEM SHALL** enforce rate limit of 100 requests per minute per API key, returning HTTP 429 with Retry-After header when exceeded, using token bucket algorithm.

#### NFR-006: Security - Input Validation
**THE SYSTEM SHALL** validate all request bodies using Pydantic schemas with type checking, string length constraints, and value ranges, rejecting malformed requests with HTTP 422 and detailed error messages.

#### NFR-007: Reliability - Data Persistence
**THE SYSTEM SHALL** persist all validation results, proposals, and task states to SQLite before returning API responses, using transactional writes with rollback on error.

#### NFR-008: Usability - Korean Language Support
**THE SYSTEM SHALL** preserve Korean compound technical terms during keyword extraction using regex patterns for "/" separated terms and domain-specific term dictionaries.

---

## 3. Specifications

### 3.1 Data Model Specifications

#### Topic Model
```yaml
Topic:
  id: str (uuid)
  metadata:
    file_path: str
    file_name: str
    folder: str
    domain: str  # one of 9 domains
  content:
    리드문: str (30-200 chars)
    정의: str (50-500 chars)
    키워드: list[str] (3-10 items)
    해시태그: str (1+ required)
    암기: str (50+ chars)
  completion:
    리드문: bool
    정의: bool
    키워드: bool
    해시태그: bool
    암기: bool
  embedding: list[float] (768-dim)
  last_validated: datetime (optional)
  validation_score: float (0.0-1.0, optional)
  created_at: datetime
  updated_at: datetime (optional)
```

#### ValidationResult Model
```yaml
ValidationResult:
  id: str (uuid)
  topic_id: str (references Topic.id)
  overall_score: float (0.0-1.0)
  gaps: list[ContentGap]
  matched_references: list[str] (reference IDs)
  validation_timestamp: datetime
  created_at: datetime
```

#### EnhancementProposal Model
```yaml
EnhancementProposal:
  id: str (uuid)
  topic_id: str (references Topic.id)
  priority: enum[CRITICAL, HIGH, MEDIUM, LOW]
  title: str
  description: str
  current_content: str
  suggested_content: str
  reasoning: str
  reference_sources: list[str]
  estimated_effort: int (minutes)
  confidence: float (0.0-1.0)
  created_at: datetime
  updated_at: datetime (optional)
```

### 3.2 API Endpoint Specifications

#### POST /api/v1/topics/upload
**Purpose:** Upload Obsidian Dataview JSON export

**Request:**
```json
{
  "topics": [
    {
      "metadata": { "file_path": "...", "file_name": "...", "folder": "...", "domain": "네트워크" },
      "content": { "리드문": "...", "정의": "...", "키워드": [...], "해시태그": "...", "암기": "..." }
    }
  ]
}
```

**Response:** 201 Created
```json
{
  "uploaded_count": 50,
  "failed_count": 0,
  "topic_ids": ["uuid-1", "uuid-2", ...]
}
```

#### POST /api/v1/validate
**Purpose:** Request validation for specified topics

**Request:**
```json
{
  "topic_ids": ["uuid-1", "uuid-2"],
  "domain_filter": null,
  "reference_domains": ["all"]
}
```

**Response:** 202 Accepted
```json
{
  "task_id": "validation-task-uuid",
  "status": "queued",
  "estimated_time_seconds": 45
}
```

#### GET /api/v1/validate/{task_id}
**Purpose:** Poll validation task status

**Response:** 200 OK
```json
{
  "task_id": "validation-task-uuid",
  "status": "in_progress",
  "progress": { "current": 5, "total": 10 }
}
```

#### GET /api/v1/validate/{task_id}/result
**Purpose:** Retrieve completed validation results

**Response:** 200 OK (when status=completed)
```json
{
  "task_id": "validation-task-uuid",
  "status": "completed",
  "results": [
    {
      "topic_id": "uuid-1",
      "overall_score": 0.65,
      "gaps": [...],
      "matched_references": [...]
    }
  ]
}
```

#### GET /api/v1/proposals
**Purpose:** Retrieve enhancement proposals for a topic

**Query Parameters:** topic_id (required), priority (optional)

**Response:** 200 OK
```json
{
  "proposals": [
    {
      "id": "proposal-uuid",
      "priority": "HIGH",
      "title": "키워드 보강 필요",
      "suggested_content": "TCP/IP, OSI 7계층, 패킷...",
      "estimated_effort": 15
    }
  ]
}
```

### 3.3 Algorithm Specifications

#### Field-Weighted Embedding Strategy
```python
# Weights: definition=0.35, lead=0.25, keywords=0.25, hashtag=0.10, memory=0.05
weighted_text = (
    topic.content.정의 * 0.35 +
    topic.content.리드문 * 0.25 +
    " ".join(topic.content.키워드) * 0.25 +
    topic.content.해시태그 * 0.10 +
    topic.content.암기 * 0.05
)
embedding = EmbeddingService.encode(weighted_text)
```

#### Trust Score Integration
```python
# Adjust similarity score by reference trust
final_score = similarity_score * (0.7 + 0.3 * reference.trust_score)
# Trust scores: PDF_BOOK=1.0, BLOG=0.8, MARKDOWN=0.6
```

#### Document Chunking Strategy
```python
# For documents > 5000 chars, use overlapping chunks
if len(document.content) > 5000:
    chunks = split_with_overlap(document.content, chunk_size=4000, overlap=500)
    embeddings = [encode(c) for c in chunks]
    best_match_index = argmax(cosine_similarity(topic_embedding, embeddings))
```

---

## 4. Traceability

**Requirements Traceability Matrix:**

| ID | Requirement | Component | Test Case |
|----|-------------|-----------|-----------|
| FR-001 | Topic Data Extraction | TopicSearchService | TC-001 |
| FR-002 | Reference Processing | PDFParser, EmbeddingService | TC-002 |
| FR-003 | Semantic Matching | MatchingService | TC-003 |
| FR-004 | Content Validation | ValidationEngine | TC-004 |
| FR-005 | Proposal Generation | ProposalGenerator | TC-005 |
| FR-006 | Keyword Suggestion | ProposalGenerator.generate_with_llm | TC-006 |
| FR-007 | Result Storage | Repository pattern | TC-007 |
| FR-008 | API Delivery | FastAPI endpoints | TC-008 |
| NFR-001 | Topic Matching Performance | All services | TC-PERF-001 |
| NFR-002 | API Response Performance | API layer | TC-PERF-002 |
| NFR-003 | Graceful Degradation | Fallback handlers | TC-DEG-001 |
| NFR-004 | API Authentication | Security middleware | TC-SEC-001 |
| NFR-005 | Rate Limiting | Rate limiter | TC-SEC-002 |
| NFR-006 | Input Validation | Pydantic schemas | TC-SEC-003 |
| NFR-007 | Data Persistence | ORM repositories | TC-REL-001 |
| NFR-008 | Korean Support | Preprocessing pipeline | TC-I18N-001 |

---

**Document Status:** Draft
**Next Review:** After implementation of P0 items from SPEC-REVIEW-001
