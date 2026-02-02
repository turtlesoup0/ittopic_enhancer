# Project Structure & Organization

**Version:** 1.0.0
**Last Updated:** 2026-02-02

---

## Repository Structure

```
itpe-topic-enhancement/
├── README.md
├── DESIGN.md
├── TECH_STACK.md
├── PROJECT_STRUCTURE.md
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── backend/                         # Python FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── dependencies.py          # Dependency injection
│   │   │
│   │   ├── api/                     # API Layer
│   │   │   ├── __init__.py
│   │   │   ├── deps.py              # API dependencies
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── api.py           # API router aggregation
│   │   │       └── endpoints/
│   │   │           ├── topics.py    # Topic CRUD endpoints
│   │   │           ├── validation.py # Validation endpoints
│   │   │           ├── proposals.py  # Proposal endpoints
│   │   │           └── references.py # Reference management
│   │   │
│   │   ├── core/                    # Core Configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Settings (Pydantic Settings)
│   │   │   ├── security.py          # Authentication/Authorization
│   │   │   └── logging.py           # Structured logging
│   │   │
│   │   ├── models/                  # Pydantic Models (Schemas)
│   │   │   ├── __init__.py
│   │   │   ├── topic.py
│   │   │   ├── reference.py
│   │   │   ├── validation.py
│   │   │   └── proposal.py
│   │   │
│   │   ├── db/                      # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base ORM model
│   │   │   ├── session.py           # DB session management
│   │   │   ├── models/              # SQLAlchemy ORM models
│   │   │   │   ├── topic.py
│   │   │   │   ├── reference.py
│   │   │   │   └── validation.py
│   │   │   └── repositories/        # Repository Pattern
│   │   │       ├── topic.py
│   │   │       └── reference.py
│   │   │
│   │   ├── services/                # Business Logic
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── parser/              # Document Parsing
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # Parser interface
│   │   │   │   ├── pdf_parser.py
│   │   │   │   ├── markdown_parser.py
│   │   │   │   └── html_parser.py
│   │   │   │
│   │   │   ├── matching/            # Embedding & Matching
│   │   │   │   ├── __init__.py
│   │   │   │   ├── embedding.py     # Embedding generation
│   │   │   │   ├── similarity.py    # Similarity calculation
│   │   │   │   └── matcher.py       # Topic-Reference matcher
│   │   │   │
│   │   │   ├── validation/          # Content Validation
│   │   │   │   ├── __init__.py
│   │   │   │   ├── rules.py         # Validation rules
│   │   │   │   ├── engine.py        # Validation engine
│   │   │   │   └── scorer.py        # Scoring logic
│   │   │   │
│   │   │   └── proposal/            # Proposal Generation
│   │   │       ├── __init__.py
│   │   │       ├── analyzer.py      # Gap analysis
│   │   │       ├── generator.py     # LLM-based generation
│   │   │       └── ranker.py        # Priority ranking
│   │   │
│   │   ├── tasks/                   # Background Tasks (Celery)
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   └── workers/
│   │   │       ├── validation.py
│   │   │       └── indexing.py
│   │   │
│   │   └── utils/                   # Utilities
│   │       ├── __init__.py
│   │       ├── cache.py
│   │       └── helpers.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_parsers.py
│   │   │   ├── test_matching.py
│   │   │   ├── test_validation.py
│   │   │   └── test_proposals.py
│   │   ├── integration/
│   │   │   ├── test_api.py
│   │   │   └── test_db.py
│   │   └── e2e/
│   │       └── test_workflow.py
│   │
│   ├── scripts/
│   │   ├── init_db.py               # Database initialization
│   │   ├── index_references.py      # Reference indexing
│   │   └── migrate_data.py
│   │
│   ├── alembic/                     # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
│
├── frontend/                        # React Frontend
│   ├── src/
│   │   ├── app/                     # Next.js App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Dashboard
│   │   │   ├── globals.css
│   │   │   ├── topics/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   ├── validation/
│   │   │   │   └── page.tsx
│   │   │   └── proposals/
│   │   │       └── page.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   └── ...
│   │   │   ├── topics/
│   │   │   │   ├── TopicList.tsx
│   │   │   │   ├── TopicCard.tsx
│   │   │   │   └── TopicFilter.tsx
│   │   │   ├── validation/
│   │   │   │   ├── ValidationResults.tsx
│   │   │   │   ├── GapList.tsx
│   │   │   │   └── ScoreBar.tsx
│   │   │   └── proposals/
│   │   │       ├── ProposalList.tsx
│   │   │       ├── ProposalCard.tsx
│   │   │       └── ApplyDialog.tsx
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts               # API client (axios)
│   │   │   ├── store.ts             # Zustand stores
│   │   │   ├── query.ts             # React Query setup
│   │   │   └── utils.ts             # Utility functions
│   │   │
│   │   ├── types/
│   │   │   └── api.ts               # TypeScript types
│   │   │
│   │   └── hooks/
│   │       ├── useTopics.ts
│   │       ├── useValidation.ts
│   │       └── useProposals.ts
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── README.md
│
├── obsidian-plugin/                 # Obsidian Plugin
│   ├── src/
│   │   ├── main.ts                  # Plugin entry point
│   │   ├── settings.ts              # Settings UI
│   │   ├── api.ts                   # Backend API client
│   │   ├── views/
│   │   │   ├── ValidationModal.ts
│   │   │   └── ProposalModal.ts
│   │   └── utils/
│   │       ├── json-exporter.ts
│   │       └── markdown-updater.ts
│   ├── manifest.json
│   └── README.md
│
├── config/
│   ├── validation_rules.yaml        # 기술사 관점 validation rules
│   ├── domains.yaml                 # Domain configuration
│   └── prompts/
│       ├── proposal_system.txt      # System prompt for proposals
│       └── validation_system.txt    # System prompt for validation
│
├── data/                            # Data Directory (gitignored)
│   ├── chromadb/                    # Vector database
│   ├── itpe-enhancement.db          # SQLite database
│   └── exports/                     # Exported JSON files
│
├── docs/                            # Documentation
│   ├── api/
│   │   └── openapi.json
│   ├── user-guide.md
│   └── developer-guide.md
│
├── scripts/                         # Utility Scripts
│   ├── dev-setup.sh
│   ├── backup.sh
│   └── deploy.sh
│
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

---

## Module Descriptions

### Backend Modules

#### API Layer (`app/api/`)
- **Purpose:** HTTP interface for frontend and plugins
- **Responsibilities:** Request validation, response formatting, error handling
- **Key Files:**
  - `api.py`: Aggregates all routers
  - `deps.py`: Dependency injection (database session, authentication)
  - `endpoints/`: Route handlers grouped by resource

#### Core (`app/core/`)
- **Purpose:** Application-wide configuration and utilities
- **Key Files:**
  - `config.py`: Pydantic-based settings management
  - `logging.py`: Structured logging configuration
  - `security.py`: API key validation, rate limiting

#### Models (`app/models/`)
- **Purpose:** Pydantic schemas for request/response validation
- **Naming Convention:** `{Resource}Request`, `{Resource}Response`, `{Resource}Create`
- **Example:** `TopicCreate`, `TopicResponse`, `TopicUpdate`

#### Database (`app/db/`)
- **Purpose:** Data persistence layer
- **Pattern:** Repository pattern for clean separation
- **Key Files:**
  - `session.py`: Async session factory
  - `models/`: SQLAlchemy ORM models
  - `repositories/`: Data access logic

#### Services (`app/services/`)
- **Purpose:** Business logic implementation
- **Subdirectories:**
  - `parser/`: Document parsing (PDF, Markdown, HTML)
  - `matching/`: Embedding generation and similarity matching
  - `validation/`: Content validation and gap detection
  - `proposal/`: Proposal generation and ranking

#### Tasks (`app/tasks/`)
- **Purpose:** Background job processing
- **Technology:** Celery with Redis broker
- **Workers:**
  - `validation.py`: Async validation tasks
  - `indexing.py`: Reference document indexing

---

### Frontend Modules

#### App Router (`src/app/`)
- **Purpose:** Next.js 16 app routing
- **File Structure:** File-based routing (page.tsx, layout.tsx)
- **Key Pages:**
  - `page.tsx`: Dashboard/home
  - `topics/`: Topic management
  - `validation/`: Validation results
  - `proposals/`: Proposal review

#### Components (`src/components/`)
- **UI Components:** shadcn/ui primitives
- **Feature Components:** Domain-specific components
- **Organization:** Grouped by feature (topics, validation, proposals)

#### Libraries (`src/lib/`)
- **API Client:** Axios-based HTTP client
- **Store:** Zustand state management
- **Query:** React Query for server state
- **Utils:** Helper functions

---

### Obsidian Plugin (`obsidian-plugin/`)

**Purpose:** Native Obsidian integration

**Key Features:**
- Automatic JSON export from Dataview
- One-click validation requests
- Proposal application (updates markdown files)
- Validation status indicator in topic headers

**Manifest:**
```json
{
  "id": "itpe-topic-enhancement",
  "name": "ITPE Topic Enhancement",
  "version": "1.0.0",
  "minAppVersion": "1.5.0",
  "description": "Validate and enhance ITPE topics with AI",
  "author": "ITPE Team"
}
```

---

## Configuration Files

### Backend Configuration

**pyproject.toml:**
```toml
[project]
name = "itpe-enhancement-backend"
version = "1.0.0"
requires-python = ">=3.13"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Frontend Configuration

**package.json:**
```json
{
  "name": "itpe-enhancement-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest",
    "lint": "eslint ."
  }
}
```

### Docker Configuration

**docker-compose.yml:**
- Orchestrates all services (backend, frontend, redis, chromadb, nginx)
- Volume mounts for development
- Environment variable management

---

## Development Workflow

### Setup

```bash
# Clone repository
git clone <repo-url>
cd itpe-topic-enhancement

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend setup
cd ../frontend
npm install

# Start services
docker-compose up -d redis chromadb

# Run backend
cd ../backend
uvicorn app.main:app --reload --port 8000

# Run frontend (new terminal)
cd frontend
npm run dev
```

### Development Commands

**Backend:**
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Lint
ruff check app/
ruff format app/

# Type check
mypy app/
```

**Frontend:**
```bash
# Run tests
npm run test

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

---

## Git Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Production hotfixes

### Commit Convention

```
feat: add proposal generator service
fix: resolve embedding memory leak
docs: update API documentation
refactor: simplify validation engine
test: add integration tests for API
```

---

**Document Status:** Complete
**Last Updated:** 2026-02-02
