# SPEC-TOPIC-001: Acceptance Criteria

---

## TAG BLOCK

```
TAG: SPEC-TOPIC-001
Related: spec.md, plan.md
Format: Given-When-Then (Gherkin)
```

---

## 1. Functional Requirements Acceptance Criteria

### AC-001: Topic Data Extraction

**Scenario:** Extract topic from Obsidian Dataview JSON export

```
GIVEN a valid Obsidian Dataview JSON export with 50 topics
WHEN the user uploads the JSON via POST /api/v1/topics/upload
THEN the system SHALL parse all 50 topics successfully
AND the system SHALL validate required fields (metadata, content)
AND the system SHALL store topics in SQLite with proper IDs
AND the system SHALL return HTTP 201 with uploaded_count=50
AND the system SHALL return 0 for failed_count
```

**Scenario:** Reject malformed topic data

```
GIVEN a JSON upload with missing required field (e.g., no "domain")
WHEN the user uploads via POST /api/v1/topics/upload
THEN the system SHALL reject the request with HTTP 422
AND the system SHALL return error message specifying missing field
AND the system SHALL not store any topics from the batch
```

---

### AC-002: Reference Document Processing

**Scenario:** Process PDF reference and generate embedding

```
GIVEN a FB21 textbook PDF file with 100 pages
WHEN the system processes the reference via POST /api/v1/references/index
THEN the system SHALL extract text content from all pages
AND the system SHALL generate 768-dim embedding using multilingual-MPNet
AND the system SHALL store the reference in ChromaDB with metadata
AND the system SHALL return HTTP 201 with reference_id
```

**Scenario:** Handle large document with chunking

```
GIVEN a reference document with 10,000 characters
WHEN the system processes the reference
THEN the system SHALL split content into overlapping chunks (4000 char, 500 overlap)
AND the system SHALL generate embedding for each chunk separately
AND the system SHALL match topic against best-scoring chunk
AND the system SHALL store chunk_index in metadata
```

---

### AC-003: Semantic Topic-Reference Matching

**Scenario:** Find similar references for topic

```
GIVEN a topic about "FDM (Frequency Division Multiplexing)" in Korean
AND 5 FB21 textbook references indexed in ChromaDB
AND similarity threshold = 0.7
WHEN the system validates the topic
THEN the system SHALL find at least 2 references with similarity > 0.7
AND the system SHALL apply trust_score adjustment: final = similarity * (0.7 + 0.3 * trust)
AND the system SHALL return references ordered by adjusted score
```

**Scenario:** Field-weighted embedding affects matching

```
GIVEN two similar topics with different field distributions
WHEN the system generates embeddings
THEN the system SHALL apply higher weight to 정의 (0.35) than 해시태그 (0.10)
AND the system SHALL verify weight impact on matching results via test
```

---

### AC-004: Content Validation

**Scenario:** Detect missing keyword gap

```
GIVEN a topic with only 1 keyword (minimum required = 3)
AND matched references with relevant technical terms
WHEN the system validates the topic
THEN the system SHALL detect MISSING_KEYWORDS gap
AND the system SHALL return gap with suggested keywords from references
AND the system SHALL set confidence > 0.7
```

**Scenario:** Detect insufficient depth gap

```
GIVEN a topic with definition length = 30 characters
AND domain-specific minimum = 100 characters for database topics
AND matched references with detailed explanations
WHEN the system validates the topic
THEN the system SHALL detect INSUFFICIENT_DEPTH gap
AND the system SHALL reference the detailed content from references
```

**Scenario:** Score validation result

```
GIVEN a validated topic with 2 gaps
WHEN the system calculates overall_score
THEN the system SHALL compute: field_completeness * 0.3 + content_accuracy * 0.4 + reference_coverage * 0.2 + technical_depth * 0.1
AND the system SHALL return score between 0.0 and 1.0
```

---

### AC-005: Enhancement Proposal Generation

**Scenario:** Generate LLM-based proposal for critical gap

```
GIVEN a CRITICAL priority gap (missing definition)
AND LLM service available
WHEN the system generates proposals
THEN the system SHALL call LLM with domain-specific prompt
THEN the system SHALL parse LLM JSON response into EnhancementProposal
AND the system SHALL include suggested_content from LLM
AND the system SHALL include reasoning field
AND the system SHALL set estimated_effort based on gap size
```

**Scenario:** Fall back to template when LLM unavailable

```
GIVEN a HIGH priority gap
AND LLM service timeout after 3 retries
WHEN the system generates proposals
THEN the system SHALL fall back to template-based generation
AND the system SHALL log fallback event with timestamp and reason
AND the system SHALL return proposal with template suggested_content
```

---

### AC-006: Keyword Suggestion

**Scenario:** Suggest domain-specific keywords

```
GIVEN a network topic about "TCP/IP"
AND matched references containing network terminology
WHEN the system generates keyword suggestions
THEN the system SHALL extract keywords relevant to network domain
AND the system SHALL preserve compound term "TCP/IP" (not split)
AND the system SHALL return 5-10 suggested keywords
AND the system SHALL include reasoning for each keyword
```

---

### AC-007: Validation Result Storage

**Scenario:** Persist validation results before response

```
GIVEN a completed validation with 3 gaps and 2 proposals
WHEN the system returns validation result
THEN the system SHALL have persisted ValidationResult to SQLite
AND the system SHALL have persisted 3 ContentGap records with foreign key
AND the system SHALL have persisted 2 EnhancementProposal records
AND the system SHALL use transaction with rollback on error
```

**Scenario:** Cache LLM responses

```
GIVEN a proposal generated via LLM for gap type MISSING_KEYWORDS
WITH topic_id = "topic-123", reference_hash = "abc123"
WHEN the same validation is requested again within 24 hours
THEN the system SHALL retrieve cached LLM response
AND the system SHALL not call LLM API again
AND the system SHALL return cached proposal
```

---

### AC-008: API Response Delivery

**Scenario:** Poll validation task progress

```
GIVEN a validation task for 10 topics
WHEN client polls GET /api/v1/validate/{task_id}
THEN the system SHALL return status="in_progress"
AND the system SHALL return progress with current and total counts
AND the system SHALL return HTTP 200
```

**Scenario:** Retrieve completed validation results

```
GIVEN a completed validation task
WHEN client calls GET /api/v1/validate/{task_id}/result
THEN the system SHALL return status="completed"
AND the system SHALL return results array with overall_score per topic
AND the system SHALL return gaps array per topic
AND the system SHALL return matched_references array per topic
```

---

## 2. Non-Functional Requirements Acceptance Criteria

### AC-NFR-001: Performance - Topic Matching

**Scenario:** Single topic matching within 5 seconds

```
GIVEN a topic requiring validation
AND 100 indexed references in ChromaDB
WHEN the system performs matching
THEN the operation SHALL complete within 5 seconds
INCLUDING embedding generation, vector search, and ranking
```

**Scenario:** Batch 100 topics within 10 minutes

```
GIVEN 100 topics to validate
AND Celery workers = 4
WHEN the system processes batch validation
THEN the operation SHALL complete within 10 minutes
AND progress updates SHALL be available via polling endpoint
```

---

### AC-NFR-002: Performance - API Response

**Scenario:** Read endpoint p95 < 200ms

```
GIVEN 1000 requests to GET /api/v1/topics
AFTER warm-up period (100 requests)
WHEN measuring response times
THEN 95th percentile SHALL be < 200ms
EXCLUDING LLM API latency
```

---

### AC-NFR-003: Availability - Graceful Degradation

**Scenario:** LLM service unavailable

```
GIVEN LLM service timeout or returns error
WHEN the system attempts proposal generation
THEN the system SHALL fall back to template-based generation
AND the system SHALL log fallback event with timestamp
AND the system SHALL continue operation without crash
```

**Scenario:** ChromaDB query fails

```
GIVEN ChromaDB service unavailable
WHEN the system attempts reference matching
THEN the system SHALL fall back to TF-IDF search
AND the system SHALL log degraded mode event
AND the system SHALL return results with lower quality
```

---

### AC-NFR-004: Security - API Authentication

**Scenario:** Require API key for write operations

```
GIVEN a request to POST /api/v1/validate
WITHOUT X-API-Key header
WHEN the system processes the request
THEN the system SHALL return HTTP 401 Unauthorized
AND the system SHALL return error message "Missing API key"
```

**Scenario:** Validate API key against stored hash

```
GIVEN a request with X-API-Key header
WHEN the system validates the key
THEN the system SHALL compare SHA-256 hash with stored values
AND valid key SHALL proceed to request handler
AND invalid key SHALL return HTTP 401
```

---

### AC-NFR-005: Security - Rate Limiting

**Scenario:** Enforce 100 requests per minute

```
GIVEN an API key with 100 requests made in current minute
WHEN the 101st request is made
THEN the system SHALL return HTTP 429 Too Many Requests
AND the system SHALL include Retry-After header with seconds until reset
```

**Scenario:** Token bucket algorithm

```
GIVEN rate limit configured as 100 requests/minute
WITH token bucket refill rate = 100/60 per second
WHEN requests are made at varying rates
THEN the system SHALL allow burst up to 100 tokens
AND the system SHALL refill tokens continuously
```

---

### AC-NFR-006: Security - Input Validation

**Scenario:** Reject malformed request body

```
GIVEN a POST request with invalid field type
WHEN the system processes the request
THEN the system SHALL validate using Pydantic schema
AND the system SHALL return HTTP 422 Unprocessable Entity
AND the system SHALL return detailed error messages listing invalid fields
```

**Scenario:** Validate string length constraints

```
GIVEN a topic upload with 리드문 = 5 characters (min 30 required)
WHEN the system validates the input
THEN the system SHALL reject the request
AND the system SHALL specify "리드문 must be at least 30 characters"
```

---

### AC-NFR-007: Reliability - Data Persistence

**Scenario:** Persist before API response

```
GIVEN a validation result ready to return
WHEN the system sends HTTP response
THEN the system SHALL have already persisted to SQLite
AND database transaction SHALL be committed
```

**Scenario:** Rollback on error

```
GIVEN an error during validation result persistence
WHEN the error occurs mid-transaction
THEN the system SHALL rollback all database changes
AND the system SHALL return HTTP 500 with error message
AND no partial data SHALL be persisted
```

---

### AC-NFR-008: Usability - Korean Language Support

**Scenario:** Preserve compound technical terms

```
GIVEN Korean text containing "TCP/IP 프로토콜"
WHEN the system extracts keywords
THEN the system SHALL preserve "TCP/IP" as single term
AND the system SHALL not split into "TCP" and "IP"
```

**Scenario:** Domain-specific term dictionary

```
GIVEN a network topic with keyword "네트워크"
AND synonym dictionary: {"네트워크": ["NW", "망", "network"]}
WHEN the system processes keywords
THEN the system SHALL recognize all variants as equivalent
AND the system SHALL normalize to canonical form
```

---

## 3. Quality Gates

### 3.1 Definition of Done

A requirement is considered complete when:

- [ ] Unit tests written and passing (pytest)
- [ ] Integration tests written and passing
- [ ] Code review completed
- [ ] LSP checks pass (zero errors, zero type errors)
- [ ] Coverage >= 85% for new code
- [ ] Documentation updated (API docs, code comments)
- [ ] Acceptance criteria from this document verified

### 3.2 Test Coverage Requirements

**Unit Tests:**
- All service methods with edge cases
- All API endpoints with valid/invalid inputs
- All validation rules per domain
- Repository CRUD operations

**Integration Tests:**
- End-to-end validation workflow
- LLM integration with mock
- ChromaDB query operations
- Database transactions

**Performance Tests:**
- Single topic matching < 5 seconds
- Batch 100 topics < 10 minutes
- API p95 response < 200ms

**Security Tests:**
- Authentication bypass attempts
- Rate limit enforcement
- SQL injection prevention
- XSS prevention

---

**Document Status:** Draft
**Next Update:** Test execution phase
