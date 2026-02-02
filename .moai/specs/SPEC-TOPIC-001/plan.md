# SPEC-TOPIC-001: Implementation Plan

---

## TAG BLOCK

```
TAG: SPEC-TOPIC-001
Related: spec.md, acceptance.md
Phase: Planning
```

---

## 1. Implementation Milestones

### Priority 1: Foundation (P0 from SPEC-REVIEW-001)

**Objective:** Resolve critical design contradictions and establish stable algorithm specifications.

**Milestone Items:**
- [ ] Resolve `auto_apply` contradiction (validation_rules.yaml vs DESIGN.md)
- [ ] Define field-weighted embedding strategy with configurable weights
- [ ] Integrate trust_score into matching algorithm
- [ ] Implement missing gap types (INSUFFICIENT_DEPTH, MISSING_EXAMPLE, INCONSISTENT_CONTENT)
- [ ] Unify similarity thresholds across MatchingService and TopicSearchService
- [ ] Implement document chunking for large references (>5000 chars)

**Success Criteria:**
- No contradictions between DESIGN.md and validation_rules.yaml
- All GapType enum values have detection logic
- Matching algorithm specifications documented in DESIGN.md
- Unit tests pass for field-weighted embeddings and trust_score integration

---

### Priority 2: LLM Integration (P0 from SPEC-REVIEW-001)

**Objective:** Activate LLM pipeline for intelligent proposal generation.

**Milestone Items:**
- [ ] Connect `generate_with_llm()` in ProposalGenerator to main flow
- [ ] Implement domain-specific prompt selection (6+ domains)
- [ ] Define JSON output schema for LLM responses
- [ ] Implement LLM response parsing with retry logic (max 2)
- [ ] Implement LLM caching by (topic_id, gap_type, reference_hash)
- [ ] Add Ollama local LLM support as alternative provider

**Success Criteria:**
- `generate_proposals()` calls LLM for CRITICAL/HIGH priority gaps
- LLM responses parsed into EnhancementProposal fields
- Template fallback works when LLM unavailable
- Cache hit on repeated validation requests

---

### Priority 3: Keyword Enhancement (P0 from SPEC-REVIEW-001)

**Objective:** Replace placeholder keyword text with actual suggestions.

**Milestone Items:**
- [ ] Implement domain-aware keyword extraction from matched references
- [ ] Add compound term preservation (e.g., "TCP/IP", "REST API")
- [ ] Implement keyword quality scoring (domain relevance, exam frequency)
- [ ] Return top 5-10 keywords with reasoning

**Success Criteria:**
- MISSING_KEYWORDS gap includes 5+ specific keyword suggestions
- Keywords relevant to topic domain
- Compound terms preserved intact

---

### Priority 4: API Security (NFR-004, NFR-005, NFR-006)

**Objective:** Implement authentication, rate limiting, and input validation.

**Milestone Items:**
- [ ] Implement X-API-Key header authentication with SHA-256 validation
- [ ] Implement token bucket rate limiter (100 req/min per key)
- [ ] Add Pydantic validation for all request bodies
- [ ] Return HTTP 422 with detailed error messages on validation failure
- [ ] Configure CORS with allowed origins whitelist

**Success Criteria:**
- All POST/PUT/DELETE endpoints require API key
- Rate limit enforced with 429 response on excess
- All malformed requests rejected before processing

---

### Priority 5: Performance Optimization (NFR-001, NFR-002)

**Objective:** Achieve specified performance targets.

**Milestone Items:**
- [ ] Implement concurrent topic validation with asyncio.gather
- [ ] Add Celery workers for batch processing (100 topics < 10 min)
- [ ] Optimize embedding generation with batch processing (batch_size=32)
- [ ] Add Redis caching for embeddings (TTL: 7 days)
- [ ] Implement response time monitoring with Prometheus

**Success Criteria:**
- Single topic matching < 5 seconds
- Batch 100 topics < 10 minutes
- API p95 response time < 200ms (read endpoints)

---

### Priority 6: Data Persistence (NFR-007)

**Objective:** Replace in-memory stores with SQLite persistence.

**Milestone Items:**
- [ ] Implement repository pattern with SQLAlchemy async
- [ ] Create migration scripts with Alembic
- [ ] Move in-memory stores (_proposals, _tasks) to database
- [ ] Implement transactional writes with rollback

**Success Criteria:**
- All validation results persisted before API response
- No data loss on service restart
- Transaction rollback on error

---

### Priority 7: Graceful Degradation (NFR-003)

**Objective:** Ensure continued operation during external service failures.

**Milestone Items:**
- [ ] Implement LLM fallback to template-based generation
- [ ] Implement ChromaDB fallback to TF-IDF search
- [ ] Add circuit breaker for external service calls
- [ ] Implement retry with exponential backoff (max 3)
- [ ] Log all fallback events with structured context

**Success Criteria:**
- System continues operating when LLM unavailable
- System continues operating when ChromaDB unavailable
- Fallback events logged for monitoring

---

## 2. Technical Approach

### 2.1 Architecture Pattern

**Layered Architecture with Repository Pattern:**

```
Presentation Layer (FastAPI)
    ↓
Business Logic Layer (Services)
    ↓
Data Access Layer (Repositories)
    ↓
Storage Layer (SQLite, ChromaDB, Redis)
```

**Rationale:** Clear separation of concerns enables independent testing and evolution of each layer.

### 2.2 Technology Stack

**Backend:**
- Python 3.13+ (JIT support, improved async)
- FastAPI 0.115+ (native async, OpenAPI)
- Pydantic 2.9+ (v2 performance)
- SQLAlchemy 2.0+ (async patterns)
- Celery 5.4+ (background tasks)

**AI/ML:**
- sentence-transformers 3.0+ (multilingual embeddings)
- ChromaDB 0.5+ (vector database)
- OpenAI 1.50+ (GPT-4o)
- Ollama (local LLM fallback)

**Infrastructure:**
- SQLite 3.45+ (embedded database)
- Redis 7.2+ (cache, task queue)
- Docker (containerization)

### 2.3 Code Organization

```
backend/app/
├── api/v1/endpoints/          # API route handlers
│   ├── topics.py              # Topic CRUD, upload
│   ├── validation.py          # Validation requests, status
│   ├── proposals.py           # Proposal retrieval
│   └── references.py          # Reference management
├── services/
│   ├── parser/                # Document parsing
│   │   ├── pdf_parser.py
│   │   └── blog_parser.py
│   ├── matching/              # Embedding & vector search
│   │   ├── embedding.py
│   │   ├── matcher.py
│   │   └── pdf_topic_matcher.py
│   ├── validation/            # Content validation
│   │   └── engine.py
│   └── proposal/              # Proposal generation
│       └── generator.py
├── db/repositories/           # Data access layer
│   ├── topic_repository.py
│   ├── validation_repository.py
│   └── proposal_repository.py
├── models/                    # Pydantic schemas
│   ├── topic.py
│   ├── reference.py
│   ├── validation.py
│   └── proposal.py
├── db/models/                 # SQLAlchemy ORM
│   ├── topic.py
│   ├── reference.py
│   ├── validation.py
│   └── proposal.py
├── core/
│   ├── config.py              # Settings management
│   ├── security.py            # Authentication, rate limiting
│   └── logging.py             # Structured logging
└── main.py                    # FastAPI app
```

### 2.4 Database Schema

**Tables:**
- `topics` (id, file_path, file_name, folder, domain, content_json, embedding_blob, ...)
- `references` (id, source_type, title, content, url, file_path, domain, embedding_blob, trust_score)
- `validations` (id, topic_id, overall_score, validation_timestamp)
- `content_gaps` (id, validation_id, gap_type, field_name, current_value, suggested_value, confidence, reference_id)
- `proposals` (id, topic_id, priority, title, description, current_content, suggested_content, reasoning, estimated_effort, confidence)
- `validation_tasks` (id, status, progress_current, progress_total, created_at)

**Relationships:**
- Topic 1:N Validation
- Validation 1:N ContentGap
- Topic 1:N Proposal

---

## 3. Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| PDF parsing quality loss | High | Medium | Multiple parser libraries (pdfplumber, PyMuPDF), OCR fallback |
| Embedding quality for Korean | High | Medium | Multilingual MPNet model, fine-tuning option if needed |
| LLM API cost overrun | Medium | High | Local LLM support, aggressive caching (24h TTL) |
| Performance bottleneck | Medium | Medium | Async processing, Redis cache, Celery workers |
| SQLite concurrency limits | Low | Low | WAL mode, connection pooling |
| ChromaDB memory usage | Medium | Low | Persistent storage, chunking large documents |

---

## 4. Dependencies

**External Dependencies:**
- Obsidian installed with Dataview plugin
- FB21 textbook PDFs available locally
- OpenAI API key (or Ollama installed locally)
- Redis server running
- ChromaDB persistent storage configured

**Internal Dependencies:**
- SPEC-REVIEW-001 P0 items completed (contradictions resolved, algorithm specified)
- Configuration files created (validation_rules.yaml, settings.yaml)

---

**Document Status:** Draft
**Next Update:** After completion of Priority 1 milestone
