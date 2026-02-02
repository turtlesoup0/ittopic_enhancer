# Technology Stack - Detailed Specification

**Version:** 1.0.0
**Last Updated:** 2026-02-02

---

## Backend Stack

### Python 3.13+

**Why Python 3.13?**
- **PEP 744 (JIT Compiler):** Experimental JIT for performance-critical operations
- **PEP 703 (GIL-free mode):** True parallel processing for CPU-bound tasks
- **Pattern Matching:** Modern `match/case` statements for cleaner code
- **Improved Type Hints:** Better IDE support and type checking

**Key Features Used:**
```python
# Pattern matching for validation logic
match gap_type:
    case GapType.MISSING_FIELD:
        priority = ProposalPriority.CRITICAL
    case GapType.INCOMPLETE_DEFINITION:
        priority = ProposalPriority.HIGH
    case _:
        priority = ProposalPriority.MEDIUM

# Async for concurrent processing
async def validate_topics(topics: List[Topic]) -> List[ValidationResult]:
    tasks = [validate_topic(t) for t in topics]
    return await asyncio.gather(*tasks)
```

### FastAPI 0.115+

**Why FastAPI?**
- **Native Async:** High performance for I/O-bound operations
- **Automatic OpenAPI:** Self-documenting API
- **Type Safety:** Pydantic integration for request/response validation
- **Dependency Injection:** Clean separation of concerns

**Project Structure:**
```
backend/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── topics.py
│   │   │   │   ├── validation.py
│   │   │   │   ├── proposals.py
│   │   │   │   └── references.py
│   │   │   └── api.py          # API router aggregation
│   ├── core/
│   │   ├── config.py           # Settings management
│   │   ├── security.py         # Authentication if needed
│   │   └── logging.py          # Structured logging
│   ├── models/
│   │   ├── topic.py            # Topic models
│   │   ├── reference.py        # Reference models
│   │   ├── validation.py       # Validation models
│   │   └── proposal.py         # Proposal models
│   ├── services/
│   │   ├── parser/             # Document parsing
│   │   ├── matching/           # Embedding & matching
│   │   ├── validation/         # Content validation
│   │   └── proposal/           # Proposal generation
│   ├── db/
│   │   ├── session.py          # Database session
│   │   ├── repositories/       # Data access layer
│   │   └── migrations/         # Schema migrations
│   └── tasks/
│       ├── celery_app.py       # Celery configuration
│       └── workers/            # Background tasks
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
└── README.md
```

**Dependency Management (pyproject.toml):**
```toml
[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.9.0"
sqlalchemy = "^2.0.35"
alembic = "^1.13.0"

# PDF/Document Parsing
pdfplumber = "^0.11.0"
pymupdf = "^1.24.0"
beautifulsoup4 = "^4.12.0"
markdown-it-py = "^3.0.0"

# Embedding & Vector DB
sentence-transformers = "^3.0.0"
chromadb = "^0.5.0"
numpy = "^2.1.0"

# Task Queue
celery = "^5.4.0"
redis = "^5.2.0"

# LLM Integration
openai = "^1.50.0"
ollama = "^0.4.0"

# Utilities
python-dotenv = "^1.0.0"
httpx = "^0.27.0"
structlog = "^24.4.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
ruff = "^0.8.0"
mypy = "^1.13.0"
```

### Pydantic 2.9+

**Why Pydantic v2?**
- **5-50x faster:** Rust core for performance
- **model_validate:** Unified validation API
- **from_attributes:** ORM object support
- **Type validation:** Comprehensive type checking

**v2 Migration Patterns:**
```python
# Old v1 patterns → New v2 patterns
from pydantic import BaseModel, ConfigDict

class Topic(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,      # was: orm_mode = True
        str_strip_whitespace=True,
        extra='forbid'             # was: Extra.forbid
    )

    # Field validation with Annotated
    리드문: str = Field(default="", min_length=30, max_length=200)

# Validation
topic = Topic.model_validate(orm_object)  # was: Topic.from_orm
topic = Topic.model_validate_json(json_str)  # was: Topic.parse_raw
```

### SQLAlchemy 2.0+ (Async)

**Async Patterns:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    "sqlite+aiosqlite:///./data/itpe-enhancement.db",
    echo=False
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevent detached instance errors
)

# Repository pattern
class TopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, topic_id: str) -> Topic | None:
        result = await self.session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def create(self, topic_data: TopicCreate) -> Topic:
        topic = Topic(**topic_data.model_dump())
        self.session.add(topic)
        await self.session.commit()
        await self.session.refresh(topic)
        return topic
```

### Celery 5.4+ for Background Tasks

**Task Definitions:**
```python
from celery import Celery

celery_app = Celery(
    "itpe_enhancement",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task(bind=True)
def validate_topics_task(self, topic_ids: List[str]):
    """Background validation task"""
    total = len(topic_ids)
    for i, topic_id in enumerate(topic_ids):
        try:
            validate_single_topic(topic_id)
            self.update_state(
                state='PROGRESS',
                meta={'current': i + 1, 'total': total}
            )
        except Exception as e:
            logger.error(f"Validation failed for {topic_id}: {e}")
    return {'status': 'completed', 'total': total}
```

---

## Frontend Stack

### React 19.0+ with TypeScript 5.9+

**Why React 19?**
- **Server Components:** Reduce client-side JavaScript
- **use Hook:** Unwrap promises in components
- **Actions:** Simplified form handling
- **Improved Concurrent Rendering:** Better UX

**Project Structure:**
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Dashboard
│   │   ├── topics/
│   │   │   ├── page.tsx         # Topic list
│   │   │   └── [id]/
│   │   │       └── page.tsx     # Topic detail
│   │   ├── validation/
│   │   │   └── page.tsx         # Validation results
│   │   └── proposals/
│   │       └── page.tsx         # Proposals management
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── topics/              # Topic-specific components
│   │   ├── validation/          # Validation components
│   │   └── proposals/           # Proposal components
│   ├── lib/
│   │   ├── api.ts               # API client
│   │   ├── store.ts             # Zustand stores
│   │   └── utils.ts             # Utility functions
│   ├── types/
│   │   └── api.ts               # TypeScript types from OpenAPI
│   └── styles/
│       └── globals.css
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

**React 19 Patterns:**
```tsx
// Server Component (Next.js 16 App Router)
// app/topics/page.tsx
async function TopicsPage() {
  const topics = await fetchTopics();  // Server-side fetch

  return (
    <main>
      <TopicList topics={topics} />
    </main>
  );
}

// Client Component with use hook
'use client';
import { use } from 'react';

function TopicList({ topicsPromise }: { topicsPromise: Promise<Topic[]> }) {
  const topics = use(topicsPromise);  // Suspend until resolved

  return (
    <ul>
      {topics.map(topic => (
        <TopicItem key={topic.id} topic={topic} />
      ))}
    </ul>
  );
}
```

### Vite 6.0+

**Why Vite?**
- **Fast HMR:** Instant hot module replacement
- **Optimized Builds:** Rollup-based production builds
- **Native ESM:** No bundling during development
- **Plugin Ecosystem:** Rich plugin support

**vite.config.ts:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: true,
  },
});
```

### shadcn/ui

**Why shadcn/ui?**
- **Accessible:** Radix UI primitives with ARIA attributes
- **Customizable:** Tailwind CSS for full styling control
- **Copy-Paste:** Components owned by your codebase
- **TypeScript:** Full type safety

**Installation:**
```bash
npx shadcn@latest init
npx shadcn@latest add button card input select table dialog
npx shadcn@latest add toast progress badge
```

**Usage:**
```tsx
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

function ValidationCard({ validation }: { validation: ValidationResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Validation Results</CardTitle>
      </CardHeader>
      <CardContent>
        <Progress value={validation.overall_score * 100} />
        <Button onClick={() => applyProposals(validation.id)}>
          Apply Proposals
        </Button>
      </CardContent>
    </Card>
  );
}
```

### Zustand 5.0+ for State Management

**Why Zustand?**
- **Simple:** Minimal boilerplate
- **Performant:** Unsubscribes from unused state
- **TypeScript:** First-class TS support
- **No Context:** No provider wrapping

**Store Definition:**
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ValidationState {
  validations: ValidationResult[];
  selectedValidation: ValidationResult | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchValidations: () => Promise<void>;
  selectValidation: (id: string) => void;
  clearError: () => void;
}

export const useValidationStore = create<ValidationState>()(
  persist(
    (set, get) => ({
      validations: [],
      selectedValidation: null,
      isLoading: false,
      error: null,

      fetchValidations: async () => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.getValidations();
          set({ validations: response.data, isLoading: false });
        } catch (error) {
          set({ error: error.message, isLoading: false });
        }
      },

      selectValidation: (id: string) => {
        const validation = get().validations.find(v => v.id === id);
        set({ selectedValidation: validation || null });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'validation-storage',
      partialize: (state) => ({ validations: state.validations }),
    }
  )
);
```

---

## AI/ML Stack

### Sentence Transformers 3.0+

**Model Selection:**
```python
from sentence_transformers import SentenceTransformer

# Multilingual model (Korean support)
model = SentenceTransformer(
    'sentence-transformers/paraphrase-multilingual-MPNet-base-v2'
)

# Alternative: Korean-specific model
# model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# Generate embeddings
embeddings = model.encode(
    texts=["토픽 내용", "참조 문서 내용"],
    batch_size=32,
    show_progress_bar=True,
    convert_to_numpy=True
)
```

**Performance Optimization:**
```python
# GPU acceleration (if available)
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer(model_name, device=device)

# Caching embeddings
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str) -> np.ndarray:
    return model.encode(text)
```

### ChromaDB 0.5+

**Setup:**
```python
import chromadb
from chromadb.config import Settings

# Local persistent storage
client = chromadb.PersistentClient(
    path="./data/chromadb",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# Create collection
collection = client.get_or_create_collection(
    name="references",
    metadata={"hnsw:space": "cosine"}
)

# Add documents
collection.add(
    documents=[ref.content for ref in references],
    ids=[ref.id for ref in references],
    embeddings=[ref.embedding for ref in references],
    metadatas=[
        {
            "domain": ref.domain,
            "source_type": ref.source_type,
            "trust_score": ref.trust_score
        }
        for ref in references
    ]
)

# Query
results = collection.query(
    query_embeddings=[topic_embedding],
    n_results=5,
    where={"domain": {"$eq": "네트워크"}}
)
```

### OpenAI GPT-4o

**API Integration:**
```python
from openai import AsyncOpenAI
from typing import AsyncGenerator

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def generate_proposal(
    topic: Topic,
    references: List[ReferenceDocument]
) -> EnhancementProposal:
    prompt = build_proposal_prompt(topic, references)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "당신은 정보관리기술사 시험 준비를 돕는 조교입니다."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=1000,
        response_format={"type": "json_object"}
    )

    return parse_proposal_response(response.choices[0].message.content)

# Streaming for real-time updates
async def stream_proposal_generation(
    topic: Topic
) -> AsyncGenerator[str, None]:
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[...],
        stream=True
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

**Cost Estimation:**
- GPT-4o Input: $2.50 / 1M tokens
- GPT-4o Output: $10.00 / 1M tokens
- Estimated per topic: ~1500 tokens (1000 input + 500 output)
- Cost per topic: ~$0.0075
- 100 topics: ~$0.75

### Ollama for Local LLM

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.1:8b
```

**Integration:**
```python
import httpx

async def generate_proposal_local(
    topic: Topic,
    references: List[ReferenceDocument]
) -> EnhancementProposal:
    prompt = build_proposal_prompt(topic, references)

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1000
                }
            }
        )

    return parse_proposal_response(response.json()["response"])
```

---

## DevOps Stack

### Docker & Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/itpe-enhancement.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./data:/app/data
    depends_on:
      - redis
      - chromadb

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend

volumes:
  redis_data:
  chromadb_data:
```

### Monitoring Stack

**Prometheus Configuration:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

**FastAPI Metrics:**
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

Instrumentator().instrument(app).expose(app)
```

---

## Security Considerations

### API Security

```python
# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/validate")
@limiter.limit("10/minute")
async def validate_topics(request: Request, ...):
    ...

# Input validation
from pydantic import BaseModel, Field, validator

class TopicUpload(BaseModel):
    topics: List[Topic]
    max_topics: int = Field(default=100, le=1000)

    @validator('topics')
    def validate_topics_length(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 topics per batch')
        return v
```

### Data Privacy

```python
# Sensitive data masking
import structlog

logger = structlog.get_logger()

logger.info(
    "validation_started",
    topic_id=topic.id,
    user_id="***",  # Mask user data
    file_path="***"  # Mask file paths
)

# No logging of:
# - Personal information
# - File paths (local system info)
# - API keys
```

---

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
from redis import Redis
import pickle

redis = Redis.from_url("redis://localhost:6379/0")

async def get_with_cache(
    key: str,
    fetch_func: Callable,
    ttl: int = 3600
):
    # Check cache
    cached = redis.get(key)
    if cached:
        return pickle.loads(cached)

    # Fetch data
    data = await fetch_func()

    # Store in cache
    redis.setex(key, ttl, pickle.dumps(data))

    return data

# Usage
topic = await get_with_cache(
    f"topic:{topic_id}",
    lambda: fetch_topic_from_db(topic_id),
    ttl=3600
)
```

### Batch Processing

```python
async def batch_validate_topics(
    topic_ids: List[str],
    batch_size: int = 10
) -> List[ValidationResult]:
    results = []

    for i in range(0, len(topic_ids), batch_size):
        batch = topic_ids[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            validate_topic(tid) for tid in batch
        ])
        results.extend(batch_results)

    return results
```

---

## Testing Strategy

### pytest Configuration

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=app",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=85"
]
```

### Async Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_validate_topic_endpoint(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/validate",
        json={"topic_ids": ["topic-001"]}
    )

    assert response.status_code == 202
    assert "task_id" in response.json()

@pytest.mark.asyncio
async def test_proposal_generation(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/proposals",
        params={"topic_id": "topic-001"}
    )

    assert response.status_code == 200
    proposals = response.json()
    assert len(proposals) > 0
```

---

**Document Status:** Complete
**Last Updated:** 2026-02-02
