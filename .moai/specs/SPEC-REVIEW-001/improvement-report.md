# SPEC-REVIEW-001: ITPE Topic Enhancement System - Design Improvement Report

- Document ID: SPEC-REVIEW-001
- Date: 2026-02-02
- Status: ✅ COMPLETE (All Phases Implemented)
- Last Updated: 2026-02-02 20:00 KST
- Scope: Topic-Reference Mapping, Keyword Suggestion, Validation Engine, Proposal Generator

---

## Implementation Progress Summary

### Phase 1: P0 (Critical) - ✅ COMPLETE
- [x] P0-CONTRADICTION - Design contradictions resolved (auto_apply → auto_suggest)
- [x] P0-MATCH - Matching algorithm specifications implemented (field weights, trust_score, chunking)
- [x] P0-LLM - LLM pipeline activated (Ollama support, caching, JSON parsing)
- [x] P0-KEYWORD - Keyword suggestions implemented (domain terms, LLM-based, compound term preservation)

### Phase 2: P1 (Major) - ✅ COMPLETE
- [x] P1-MODEL - Data model inconsistencies fixed (id, timestamps, ORM separation)
- [x] P1-SCORING - Validation scoring improved (semantic similarity, log scaling, domain thresholds)
- [x] P1-PRIORITY - Proposal priority enhanced (severity-aware, exam frequency, effort scaling)
- [x] P1-BLOG - Blog parsing deferred (scope reduction, BLOG type removed)

### Phase 3: P2 (Moderate) - ✅ COMPLETE
- [x] P2-SPEC - SPEC.md completed (EARS format, NFRs, security requirements)
- [x] P2-ERROR - Error handling improved (categories, retry, circuit breaker, structured logging)
- [x] P2-KOREAN - Korean language processing enhanced (compound terms, synonyms, stopwords)
- [x] P2-AUTH - API security implemented (X-API-Key, rate limiting, CORS hardening)
- [x] P2-CACHE - Caching strategy implemented (CacheManager, 83% coverage)
- [x] P2-STORAGE - DB persistence implemented (Alembic migration, 86-95% coverage)

---

# SPEC-REVIEW-001: ITPE Topic Enhancement System - Design Improvement Report

- Document ID: SPEC-REVIEW-001
- Date: 2026-02-02
- Status: Approved for Implementation
- Scope: Topic-Reference Mapping, Keyword Suggestion, Validation Engine, Proposal Generator

---

## 1. Executive Summary

ITPE Topic Enhancement System is designed to map Obsidian study topics with FB21 textbooks and blog references, validate content completeness, and suggest enhancement keywords for ITPE (Information Technology Professional Engineer) exam preparation.

Architecture and module separation are well-structured, but critical gaps exist in core business logic: matching algorithms lack specification, LLM integration is incomplete (methods exist but are never called), keyword suggestion returns placeholder text instead of actual suggestions, and scoring logic relies on naive heuristics (string length comparison) rather than semantic analysis.

This document provides a prioritized list of improvements organized by severity, with concrete requirements and acceptance criteria for each item.

---

## 2. Analysis Scope

### Files Analyzed

**Design Documents:**
- `DESIGN.md` (24.4 KB) - System architecture and design
- `SPEC.md` (1.2 KB) - Project specification
- `TECH_STACK.md` (20.7 KB) - Technology decisions
- `config/validation_rules.yaml` - Validation rule configuration
- `config/prompts/validation_system.txt` - LLM validation prompt (355 lines)
- `config/prompts/proposal_system.txt` - LLM proposal prompt (226 lines)

**Backend Services:**
- `backend/app/services/matching/embedding.py` - EmbeddingService (singleton, SentenceTransformers)
- `backend/app/services/matching/matcher.py` - MatchingService (ChromaDB cosine similarity)
- `backend/app/services/matching/pdf_topic_matcher.py` - PDF-to-topic bridge
- `backend/app/services/parser/pdf_parser.py` - PDF text extraction (pdfplumber)
- `backend/app/services/validation/engine.py` - ValidationEngine (3-layer validation)
- `backend/app/services/proposal/generator.py` - ProposalGenerator (template-based)
- `backend/app/services/vector/topic_search.py` - TopicSearchService (TF-IDF)

**Data Models:**
- `backend/app/models/topic.py` - Topic + TopicContent + TopicMetadata
- `backend/app/models/reference.py` - ReferenceDocument + MatchedReference
- `backend/app/models/validation.py` - ValidationResult + ContentGap
- `backend/app/models/proposal.py` - EnhancementProposal
- `backend/app/db/models/topic.py` - Topic ORM
- `backend/app/db/models/reference.py` - Reference + Validation + Proposal ORM
- `frontend/src/types/api.ts` - Frontend TypeScript types

---

## 3. Current Strengths

These aspects are well-designed and should be preserved during improvements:

| Aspect | Details |
|--------|---------|
| Layered Architecture | ETL -> Processing -> Storage -> API -> Presentation clearly separated |
| Data Models | Pydantic schemas with proper typing, GapType/ProposalPriority enums |
| Vector Search Foundation | ChromaDB + SentenceTransformers (multilingual-MPNet) is appropriate |
| Validation Rules Externalization | YAML-based rules allow runtime configuration changes |
| Risk Management | 9 technical risks documented with mitigation strategies |
| Phased Roadmap | MVP -> Core -> Advanced phases reduce technical risk |
| PDF Parser | pdfplumber with per-page extraction, table detection, metadata capture |

---

## 4. Critical Improvements (P0)

These items block core functionality. Must be resolved before MVP release.

---

### 4.1 [P0-KEYWORD] Keyword Suggestion Returns Placeholder Text

**Current Behavior:**
When keywords are insufficient, the system returns generic text instead of actual keyword suggestions:
```python
# backend/app/services/validation/engine.py
suggested_value="기술 관련 핵심 용어 3개 이상 필요"  # placeholder, not actual keywords
```

**Root Cause:**
- `generate_with_llm()` method exists in `ProposalGenerator` but is never called
- PDF keyword extraction uses only regex + frequency counting (no domain filtering)
- No mechanism to extract domain-specific technical terms from matched references

**Required Changes:**

1. **Connect LLM to keyword generation pipeline:**
   - In `ProposalGenerator.generate_proposals()`, call `generate_with_llm()` when gap type is `MISSING_KEYWORDS`
   - Pass matched reference content as context for keyword extraction
   - Parse LLM response into structured keyword list

2. **Implement domain-aware keyword extraction:**
   - Add domain-specific term dictionaries (per validation_rules.yaml domains)
   - Filter extracted keywords against domain vocabulary
   - Handle compound terms: "TCP/IP", "REST API" should not be split

3. **Add keyword quality scoring:**
   - Score keywords by: domain relevance, exam frequency, uniqueness
   - Rank suggestions by quality score
   - Return top 5-10 keywords with reasoning

**Acceptance Criteria:**
- [ ] `MISSING_KEYWORDS` gap includes 5+ specific keyword suggestions (not placeholder text)
- [ ] Keywords are relevant to the topic's domain (e.g., network topics get network terms)
- [ ] Compound technical terms are preserved intact
- [ ] LLM fallback returns reference-extracted keywords when API is unavailable

---

### 4.2 [P0-LLM] LLM Integration Is Defined But Never Invoked

**Current Behavior:**
- `validation_system.txt` (355 lines) and `proposal_system.txt` (226 lines) are written but unused
- `generate_with_llm()` method exists in ProposalGenerator but is never called from `generate_proposals()`
- All proposals use hardcoded template strings

**Evidence:**
```python
# backend/app/services/proposal/generator.py
# generate_proposals() creates proposals from template strings only:
proposal = EnhancementProposal(
    suggested_content=gap.suggested_value,  # copies validation gap text, no LLM
)

# generate_with_llm() exists but is unreachable from main flow
async def generate_with_llm(self, topic_name, current_content, reference_content) -> str:
    ...  # never called
```

**Required Changes:**

1. **Activate LLM pipeline in proposal generation:**
   - Modify `generate_proposals()` to call `generate_with_llm()` for HIGH and CRITICAL priority gaps
   - Use template-based generation as fallback when LLM is unavailable
   - Add structured output format (JSON schema) to LLM prompts

2. **Implement domain-specific prompt selection:**
   - Create prompt variants per domain (validation_rules.yaml defines 6+ domains)
   - Include domain-specific required_elements in prompt context
   - Example: network topics should include protocol/standard requirement in prompt

3. **Add LLM response parsing:**
   - Define JSON output schema for LLM responses
   - Parse into EnhancementProposal fields (title, description, suggested_content, reasoning)
   - Handle malformed responses with retry (max 2) then template fallback

4. **Implement LLM caching:**
   - Cache LLM responses by (topic_id, gap_type, reference_hash)
   - TTL: 24 hours (references change infrequently)
   - Invalidate when topic content changes

5. **Add Ollama local LLM support:**
   - Config already defines `ollama_base_url` but implementation is incomplete
   - Implement Ollama client as alternative to OpenAI
   - Use for development/testing without API costs

**Acceptance Criteria:**
- [ ] `generate_proposals()` calls LLM for CRITICAL and HIGH priority gaps
- [ ] LLM responses are parsed into structured EnhancementProposal fields
- [ ] Template fallback works when LLM is unavailable
- [ ] Domain-specific prompts are selected based on topic domain
- [ ] LLM responses are cached (verified by checking cache hit on repeated calls)
- [ ] Ollama local LLM works as alternative provider

---

### 4.3 [P0-MATCH] Matching Algorithm Lacks Critical Specifications

**Current Behavior:**
Matching works at a basic level (cosine similarity via ChromaDB), but key design decisions are unspecified and implementation has inconsistencies.

**Specific Issues:**

**A) Input Embedding Strategy Not Defined:**
```python
# backend/app/services/matching/matcher.py:164-189
# Current: concatenates all Korean fields into single text
parts = [topic.metadata.file_name, topic.content.리드문, topic.content.정의,
         " ".join(topic.content.키워드), topic.content.해시태그, topic.content.암기]
```
- No field weighting (definition is equally weighted to hashtags)
- No specification of whether this is optimal

**B) trust_score Has No Algorithmic Integration:**
```python
# backend/app/models/reference.py
trust_score: float = Field(default=1.0)  # defined but never used in matching
```
- Not multiplied with similarity score
- Not used for filtering or re-ranking
- Exists only as metadata

**C) Similarity Threshold Mismatch Between Systems:**
- `MatchingService` (vector): threshold = `0.7`
- `TopicSearchService` (TF-IDF): threshold = `0.01` (search) / `0.05` (similar)
- No documentation explaining the difference or when each is used

**D) Document Truncation Without Chunking:**
```python
# backend/app/services/matching/matcher.py:71
documents = [ref.content[:10000] for ref in references]  # naive truncation
```
- Loses content beyond 10K characters
- No intelligent chunking strategy

**Required Changes:**

1. **Define field-weighted embedding strategy:**
   - Assign weights: definition (0.35), lead (0.25), keywords (0.25), hashtag (0.10), memory (0.05)
   - Document rationale in DESIGN.md
   - Make weights configurable in settings

2. **Integrate trust_score into matching:**
   - Formula: `final_score = similarity_score * (0.7 + 0.3 * trust_score)`
   - This means trust_score adjusts final score by up to 30%
   - Trust score values: PDF_BOOK=1.0, BLOG=0.8, MARKDOWN=0.6
   - Document formula in DESIGN.md

3. **Unify similarity thresholds:**
   - Single config section for all thresholds
   - Document what each threshold means and when it applies
   - Add threshold calibration guide

4. **Implement document chunking:**
   - Split documents > 5000 chars into overlapping chunks (500 char overlap)
   - Embed each chunk separately
   - Match against best chunk per document
   - Store chunk_index in metadata

**Acceptance Criteria:**
- [ ] Embedding uses field-weighted strategy (configurable weights)
- [ ] trust_score affects matching results (verified with test)
- [ ] All similarity thresholds documented in single config section
- [ ] Documents > 5000 chars are chunked, not truncated
- [ ] DESIGN.md updated with algorithm specifications

---

### 4.4 [P0-CONTRADICTION] Design-Implementation Contradictions

**Issue A: auto_apply Contradicts Non-Goal:**
```yaml
# config/validation_rules.yaml
auto_enhancement:
  rules:
    - condition: "키워드_부족"
      action: "기술_용어_자동_추출"
      auto_apply: true  # contradicts non-goal
```
```
# DESIGN.md
Non-Goals: 자동으로 토픽 내용 수정 (사용자 승인 필요)
```

**Issue B: Gap Types Defined But Not Implemented:**
- `INSUFFICIENT_DEPTH` defined in validation_system.txt -> not in GapType enum
- `MISSING_EXAMPLE` defined in validation_system.txt -> not in GapType enum
- `INCONSISTENT_CONTENT` defined in validation_system.txt -> not in GapType enum

**Required Changes:**

1. **Resolve auto_apply scope:**
   - Decision needed: Remove auto_apply entirely OR redefine as "auto-suggest with user confirmation"
   - If kept, rename to `auto_suggest: true` and always require user approval
   - Update DESIGN.md non-goals to match

2. **Implement missing gap types:**
   - Add to GapType enum: `INSUFFICIENT_DEPTH`, `MISSING_EXAMPLE`, `INCONSISTENT_CONTENT`
   - Implement detection logic in ValidationEngine:
     - `INSUFFICIENT_DEPTH`: content length < domain-specific threshold AND low similarity to references
     - `MISSING_EXAMPLE`: no code blocks, tables, or example patterns detected
     - `INCONSISTENT_CONTENT`: conflicting information between fields (LLM-assisted detection)
   - Add to priority_map in ProposalGenerator

**Acceptance Criteria:**
- [ ] No contradiction between DESIGN.md non-goals and validation_rules.yaml
- [ ] GapType enum includes all types referenced in system prompts
- [ ] Each gap type has working detection logic in ValidationEngine
- [ ] Each gap type has priority mapping in ProposalGenerator

---

## 5. Major Improvements (P1)

These items significantly affect quality. Should be resolved in first development sprint.

---

### 5.1 [P1-SCORING] Validation Scoring Logic Is Too Naive

**Current Issues:**

**A) Content accuracy judged by string length:**
```python
# backend/app/services/validation/engine.py:131-134
for ref in references[:2]:  # only checks 2 references
    if ref.similarity_score > 0.8:
        if len(ref.relevant_snippet) > len(topic.content.정의) * 1.5:  # length comparison
            # creates "incomplete" gap
```
- Length does not equal quality
- Only compares against 2 references (hardcoded)

**B) Binary scoring for memory field:**
```python
memory_score = 0.5 if topic.content.암기 else 0.0  # exists = 0.5, missing = 0.0
```

**C) Coverage score saturates quickly:**
```python
coverage = min(1.0, high_quality * 0.5 + medium_quality * 0.3)
# 3 high-quality refs: 3 * 0.5 = 1.5 -> capped at 1.0 (always max)
```

**D) No domain-specific weights:**
- Database definition needs more depth than network protocol definition
- Same 50-char minimum for all domains

**Required Changes:**

1. **Replace length-based accuracy with semantic comparison:**
   - Use embedding similarity between topic field and reference snippet
   - Accuracy = average semantic similarity across all matched references (not just top 2)
   - Threshold: similarity < 0.6 = inaccurate, 0.6-0.8 = needs improvement, > 0.8 = accurate

2. **Implement graduated field scoring:**
   - Replace binary scores with length-ratio + quality assessment
   - Memory field: score by content richness (has mnemonics, acronyms, key points)
   - Keyword field: score by count AND domain relevance

3. **Fix coverage score saturation:**
   - Use logarithmic scaling: `coverage = min(1.0, 0.3 * log2(1 + high) + 0.2 * log2(1 + medium))`
   - This gives diminishing returns for additional references

4. **Add domain-specific validation thresholds:**
   - Load from validation_rules.yaml per domain
   - Example: database topics require minimum 100-char definition, network topics require 80-char
   - Make configurable without code changes

**Acceptance Criteria:**
- [ ] Accuracy score uses semantic similarity, not string length
- [ ] All matched references are considered (not hardcoded [:2])
- [ ] Coverage score differentiates between 3 and 10 high-quality references
- [ ] Domain-specific thresholds loaded from configuration
- [ ] Binary field scores replaced with graduated scoring

---

### 5.2 [P1-PRIORITY] Proposal Priority Does Not Reflect Severity

**Current Behavior:**
```python
# backend/app/services/proposal/generator.py
priority_map = {
    GapType.MISSING_KEYWORDS: ProposalPriority.HIGH,  # always HIGH regardless of count
}
```
- Missing 1 keyword = HIGH, missing 5 keywords = HIGH (same)
- No reference confidence consideration
- No exam relevance weighting

**Required Changes:**

1. **Implement severity-aware priority:**
   - Factor in gap magnitude: (missing_count / required_count) ratio
   - Factor in reference confidence: low-confidence gaps demoted one level
   - Formula: `priority = base_priority(gap_type) * severity_multiplier * confidence_weight`

2. **Add exam frequency weighting:**
   - Add `exam_frequency` field to topic metadata (optional)
   - Higher exam frequency = higher priority for gaps
   - Data source: historical exam analysis or user annotation

3. **Implement effort estimation based on actual content:**
   - Current: hardcoded (MISSING_KEYWORDS = 10 minutes always)
   - Improved: calculate based on gap magnitude and content length needed
   - Example: 5 missing keywords = 15 min, 1 missing keyword = 5 min

**Acceptance Criteria:**
- [ ] Priority reflects gap magnitude (missing 5 keywords > missing 1 keyword)
- [ ] Low-confidence reference gaps have lower priority than high-confidence ones
- [ ] Effort estimation scales with gap size

---

### 5.3 [P1-BLOG] Blog Reference Parsing Not Implemented

**Current Behavior:**
```python
# backend/app/api/v1/endpoints/references.py:52-55
else:
    # For now, only PDF is supported
    failed_count += 1
    failed_paths.append(path)
    continue
```
- `BLOG` and `MARKDOWN` source types defined in enum but no parser
- blog.skby.net referenced in config but never crawled

**Required Changes:**

1. **Implement blog content parser:**
   - Use BeautifulSoup4 (already in dependencies) for HTML parsing
   - Extract: title, main content, published date, domain/category
   - Strip navigation, ads, comments
   - Handle Korean character encoding

2. **Implement blog URL management:**
   - Store indexed URLs to prevent re-crawling
   - Track last_crawled timestamp per URL
   - Detect content updates via content hash comparison
   - Respect robots.txt and rate limits (min 1 second between requests)

3. **OR redefine scope to exclude blogs:**
   - If blog parsing is deferred, remove BLOG from ReferenceSourceType enum
   - Remove blog_skby_url from configuration
   - Document in DESIGN.md as future enhancement

**Acceptance Criteria:**
- [ ] Either: Blog parser extracts title, content, date from blog.skby.net pages
- [ ] Either: Blog references are indexed in ChromaDB with correct source_type
- [ ] OR: BLOG type removed from enum and configuration cleaned up

---

### 5.4 [P1-MODEL] Data Model Inconsistencies

**Issues Found:**

| Issue | Location | Fix |
|-------|----------|-----|
| `ValidationResult` missing `id` field | `backend/app/models/validation.py` | Add `id: str` field |
| `ValidationORM` and `ProposalORM` in wrong file | `backend/app/db/models/reference.py` | Move to separate files |
| Frontend `Topic` missing `created_at`, `embedding` | `frontend/src/types/api.ts` | Add fields |
| No `ReferenceDocument` type in frontend | `frontend/src/types/api.ts` | Add interface |
| No SQLAlchemy relationships defined | `backend/app/db/models/*.py` | Add relationship() |
| `validation_timestamp` vs `created_at` naming | API vs ORM | Standardize names |
| Missing `updated_at` in API schemas | All API models | Add field |

**Required Changes:**

1. **Fix API schemas:**
   - Add `id: str` to `ValidationResult`
   - Add `updated_at: Optional[datetime]` to Topic, Reference, Proposal, Validation
   - Standardize timestamp field names: `created_at`, `updated_at` everywhere

2. **Fix ORM models:**
   - Move `ValidationORM` to `backend/app/db/models/validation.py`
   - Move `ProposalORM` to `backend/app/db/models/proposal.py`
   - Add SQLAlchemy `relationship()` definitions between models
   - Add proper foreign key constraints

3. **Fix frontend types:**
   - Add `created_at: string` and `embedding?: number[]` to Topic
   - Add `ReferenceDocument` interface matching backend schema
   - Add `created_at: string` to Proposal
   - Add `id: string` to ValidationResult

**Acceptance Criteria:**
- [ ] All API schemas have `id` field
- [ ] All models have `created_at` and `updated_at` fields
- [ ] Each ORM model is in its own file under `backend/app/db/models/`
- [ ] Frontend types match backend API schemas (no missing fields)
- [ ] SQLAlchemy relationships defined for topic -> validation, topic -> proposal

---

## 6. Moderate Improvements (P2)

These items improve quality and maintainability. Should be planned for second sprint.

---

### 6.1 [P2-SPEC] SPEC.md Is Incomplete (14 Lines)

**Current State:**
SPEC.md contains only a brief workflow description with no formal requirements.

**Required Changes:**
- Rewrite in EARS format with Given/When/Then acceptance criteria
- Add non-functional requirements:
  - Performance: topic matching < 5 seconds, batch 100 topics < 10 minutes
  - API response: < 200ms (p95) for read endpoints
  - Availability: graceful degradation when LLM is unavailable
- Add security requirements:
  - API authentication mechanism
  - Rate limiting (100 requests/minute per client)
  - Input validation for all endpoints

---

### 6.2 [P2-CACHE] Caching Strategy Undefined

**Current State:**
```yaml
cache:
  enabled: true
  ttl_seconds: 3600
  max_size_mb: 100
```
Only TTL is configured. No cache key design, invalidation strategy, or hit rate expectations.

**Required Changes:**
- Define cache key format: `{service}:{entity_id}:{content_hash}`
- Define invalidation triggers:
  - Topic edited -> invalidate topic validation cache
  - Reference updated -> invalidate all validation caches using that reference
  - Config changed -> flush all caches
- Define what is cached:
  - Embeddings (TTL: 7 days, invalidate on content change)
  - Validation results (TTL: 1 hour, invalidate on topic/reference change)
  - LLM responses (TTL: 24 hours, invalidate on prompt change)

---

### 6.3 [P2-ERROR] Error Handling Strategy Incomplete

**Current Issues:**
- `embedding.py:140`: returns `0.0` on similarity error (silent failure)
- No retry logic for transient LLM API failures
- No circuit breaker for external service calls
- Generic exception catches without discrimination

**Required Changes:**
- Define error categories: transient (retry), permanent (fail fast), degraded (fallback)
- Implement retry with exponential backoff for LLM calls (max 3 retries)
- Add circuit breaker for ChromaDB and OpenAI connections
- Replace silent error returns with explicit error types
- Log all errors with structured context (topic_id, service, operation)

---

### 6.4 [P2-AUTH] API Security Design Missing

**Current State:**
No authentication, authorization, or rate limiting implemented.

**Required Changes:**
- Implement API key authentication for all endpoints
- Add rate limiting: 100 requests/minute per API key
- Add input validation for all request bodies (already have Pydantic, ensure enforcement)
- Add CORS configuration review (currently allows all origins)

---

### 6.5 [P2-STORAGE] In-Memory Storage Must Be Replaced

**Current State:**
```python
# backend/app/api/v1/endpoints/proposals.py
_proposals: dict[str, List[EnhancementProposal]] = {}  # lost on restart

# backend/app/api/v1/endpoints/validation.py
_tasks: dict[str, ValidationTaskStatus] = {}  # lost on restart
```

**Required Changes:**
- Migrate in-memory stores to SQLite via ORM models
- Implement repository pattern (already designed in `backend/app/db/repositories/`)
- Add database migrations via Alembic (already in dependencies)

---

### 6.6 [P2-KOREAN] Korean Language Processing Needs Improvement

**Current Issues:**
- Keyword extraction splits compound terms: "TCP/IP" -> "TCP", "IP"
- No Korean morphological analysis
- Stopword list is minimal and hardcoded
- No synonym handling: "네트워크", "NW", "망" treated as different terms

**Required Changes:**
- Add Korean-specific preprocessing:
  - Compound term preservation regex (handle "/" separated terms)
  - Consider KoNLPy or similar for morphological analysis
  - Expand stopword list with domain-specific common terms
- Add synonym mapping:
  - Maintain synonym dictionary per domain
  - Example: {"네트워크": ["NW", "망", "network"], "데이터베이스": ["DB", "DBMS"]}

---

## 7. Hardcoded Magic Numbers to Externalize

All of these values should be moved to configuration (validation_rules.yaml or settings):

| Value | Location | Current | Purpose |
|-------|----------|---------|---------|
| `30` | `engine.py:17` | 30 chars | Min lead paragraph length |
| `50` | `engine.py:18` | 50 chars | Min definition length |
| `3` | `engine.py:21` | 3 items | Min keyword count |
| `[:2]` | `engine.py:131` | 2 refs | Top references for accuracy check |
| `0.8` | `engine.py:132` | 0.8 | Similarity threshold for gap trigger |
| `1.5` | `engine.py:134` | 1.5x | Length ratio for gap trigger |
| `[:10]` | `pdf_topic_matcher.py:61` | 10 | Top keywords from PDF |
| `10000` | `matcher.py:71` | 10K chars | Document content truncation limit |
| `0.7` | `matcher.py:142` | 0.7 | Similarity match threshold |
| `0.01` | `topic_search.py:115` | 0.01 | TF-IDF search threshold |
| `0.05` | `topic_search.py:180` | 0.05 | TF-IDF similar topic threshold |
| `32` | `embedding.py` | 32 | Embedding batch size |
| `20` | `generator.py` | 20 min | Effort for MISSING_FIELD |
| `30` | `generator.py` | 30 min | Effort for INCOMPLETE_DEFINITION |
| `10` | `generator.py` | 10 min | Effort for MISSING_KEYWORDS |

**Action:** Create a `thresholds` section in `config/validation_rules.yaml` with all configurable values.

---

## 8. Implementation Order

Recommended execution sequence considering dependencies:

```
Phase 1: Foundation (P0 items)
├── [P0-CONTRADICTION] Resolve design contradictions first (unblocks all others)
├── [P0-MATCH] Define matching algorithm specs (unblocks scoring improvements)
├── [P0-LLM] Activate LLM pipeline (unblocks keyword and proposal improvements)
└── [P0-KEYWORD] Implement keyword suggestions (depends on LLM pipeline)

Phase 2: Quality (P1 items)
├── [P1-MODEL] Fix data model inconsistencies (parallel with others)
├── [P1-SCORING] Improve validation scoring (depends on P0-MATCH)
├── [P1-PRIORITY] Improve proposal priority (depends on P0-LLM, P1-SCORING)
└── [P1-BLOG] Blog parsing or scope reduction (independent)

Phase 3: Hardening (P2 items)
├── [P2-STORAGE] Replace in-memory stores (prerequisite for production)
├── [P2-ERROR] Error handling improvements (parallel)
├── [P2-CACHE] Caching strategy (depends on P2-STORAGE)
├── [P2-AUTH] API security (independent)
├── [P2-KOREAN] Korean language processing (independent)
└── [P2-SPEC] SPEC.md completion (independent)
```

---

## 9. Dependency Map

```
P0-CONTRADICTION ─┐
                   ├──> P0-MATCH ──> P1-SCORING ──> P1-PRIORITY
                   │
P0-LLM ───────────┼──> P0-KEYWORD
                   │
P1-MODEL ──────────┤ (parallel, no hard dependencies)
                   │
P1-BLOG ───────────┘ (independent)

P2-STORAGE ──> P2-CACHE
P2-ERROR, P2-AUTH, P2-KOREAN, P2-SPEC (all independent)
```

---

## 10. Files Expected to Change

### Phase 1 (P0)
- `DESIGN.md` - Algorithm specifications, contradiction resolution
- `config/validation_rules.yaml` - auto_apply -> auto_suggest, thresholds section
- `backend/app/models/validation.py` - Add INSUFFICIENT_DEPTH, MISSING_EXAMPLE, INCONSISTENT_CONTENT to GapType
- `backend/app/services/validation/engine.py` - New gap detection logic, configurable thresholds
- `backend/app/services/proposal/generator.py` - Connect LLM, domain-specific prompts, structured output
- `backend/app/services/matching/matcher.py` - Field-weighted embedding, trust_score integration, chunking
- `backend/app/core/config.py` - New configuration fields for weights, thresholds

### Phase 2 (P1)
- `backend/app/services/validation/engine.py` - Semantic scoring, graduated field scores
- `backend/app/services/proposal/generator.py` - Severity-aware priority, scaled effort estimation
- `backend/app/services/parser/blog_parser.py` - NEW FILE (or remove BLOG from enum)
- `backend/app/models/*.py` - Add missing fields (id, updated_at)
- `backend/app/db/models/validation.py` - NEW FILE (move from reference.py)
- `backend/app/db/models/proposal.py` - NEW FILE (move from reference.py)
- `frontend/src/types/api.ts` - Sync with backend schemas

### Phase 3 (P2)
- `SPEC.md` - Full rewrite in EARS format
- `backend/app/db/repositories/*.py` - Implement repository pattern
- `backend/app/api/v1/endpoints/*.py` - Replace in-memory stores with DB
- `backend/app/core/security.py` - API authentication
- `backend/app/services/matching/pdf_topic_matcher.py` - Korean processing improvements
- `config/validation_rules.yaml` - Externalized thresholds section

---

## 11. Testing Requirements per Phase

### Phase 1
- Unit tests for new gap type detection (INSUFFICIENT_DEPTH, MISSING_EXAMPLE, INCONSISTENT_CONTENT)
- Unit tests for field-weighted embedding (verify weights affect results)
- Unit tests for trust_score integration (verify scoring formula)
- Integration test: LLM pipeline end-to-end (mock LLM, verify structured output parsing)
- Integration test: keyword suggestion returns domain-specific terms

### Phase 2
- Unit tests for semantic scoring (similarity-based vs length-based)
- Unit tests for severity-aware priority calculation
- Unit tests for graduated field scoring
- Integration test: blog parsing (if implemented) end-to-end
- Contract tests: frontend types match backend API responses

### Phase 3
- Integration tests for SQLite persistence (CRUD for all models)
- Integration tests for cache invalidation
- Load tests for API rate limiting
- Security tests for authentication bypass attempts

---

## Appendix A: Current Data Flow

```
Obsidian Vault (Dataview JSON export)
    |
    v
TopicSearchService.load_from_json()
    |
    v
Topic Model (in-memory)
    |
    +---> EmbeddingService.encode(topic_text)
    |         |
    |         v
    |     768-dim vector
    |         |
    |         v
    +---> MatchingService.find_references(topic)
    |         |
    |         +---> ChromaDB.query(embedding, top_k=5)
    |         |
    |         v
    |     MatchedReference[] (similarity > 0.7)
    |         |
    v         v
ValidationEngine.validate(topic, matched_references)
    |
    +---> _check_field_completeness() --> ContentGap[]
    +---> _check_content_accuracy()   --> ContentGap[]
    +---> _calculate_scores()         --> ValidationResult
    |
    v
ProposalGenerator.generate_proposals(validation_result, references)
    |
    +---> For each gap: template-based proposal (LLM NOT connected)
    |
    v
EnhancementProposal[] (in-memory, lost on restart)
```

---

## Appendix B: Target Data Flow After Improvements

```
Obsidian Vault (Dataview JSON export)
    |
    v
TopicSearchService.load_from_json()
    |
    v
Topic Model (SQLite persisted)
    |
    +---> EmbeddingService.encode(weighted_topic_fields)   [P0-MATCH]
    |         |
    |         v
    |     768-dim vector (field-weighted)
    |         |
    |         v
    +---> MatchingService.find_references(topic)
    |         |
    |         +---> ChromaDB.query(embedding, top_k=5)
    |         +---> Apply trust_score adjustment              [P0-MATCH]
    |         +---> Domain-filtered re-ranking                [P0-MATCH]
    |         |
    |         v
    |     MatchedReference[] (adjusted scores)
    |         |
    v         v
ValidationEngine.validate(topic, matched_references)
    |
    +---> _check_field_completeness()      --> ContentGap[]
    +---> _check_content_accuracy()        --> ContentGap[] (semantic)  [P1-SCORING]
    +---> _check_depth()                   --> ContentGap[]             [P0-CONTRADICTION]
    +---> _check_examples()                --> ContentGap[]             [P0-CONTRADICTION]
    +---> _calculate_scores()              --> ValidationResult (domain-weighted)
    |
    v
ProposalGenerator.generate_proposals(validation_result, references)
    |
    +---> For CRITICAL/HIGH gaps: LLM-enhanced proposals     [P0-LLM]
    +---> For MISSING_KEYWORDS: LLM keyword extraction       [P0-KEYWORD]
    +---> For MEDIUM/LOW gaps: template-based proposals
    +---> Severity-aware priority calculation                 [P1-PRIORITY]
    |
    v
EnhancementProposal[] (SQLite persisted, cached)            [P2-STORAGE]
```
