# ITPE Topic Enhancement System

정보관리기술사 시험 준비를 위한 Obsidian 기반 토픽 관리 시스템입니다. 작성한 토픽 노트의 정확성을 검증하고 기술사 시험 수준으로 내용을 보강합니다.

## Overview

이 시스템은 다음 기능을 제공합니다:

- **참조 문서 자동 연동:** FB21 수험 서적과 블로그 자동 매칭
- **지능형 검증:** 토픽 vs 참조 문서 간의 차이 자동 분석
- **우선순위 기반 제안:** 기술사 관점에서 보강 필요 항목 추천
- **직관적인 UI:** 진행 상황 시각화 및 결과 확인

## Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        OBSIDIAN[Obsidian Vault]
        REFBOOKS[FB21 Reference Books]
        BLOG[Blog References]
    end

    subgraph "Backend"
        API[FastAPI Backend]
        EMBED[Embedding Service]
        VDB[(Vector DB)]
        LLM[LLM Service]
        CELERY[Celery Workers]
        REDIS[(Redis Broker)]
    end

    subgraph "Frontend"
        WEB[Web Dashboard]
        PLUGIN[Obsidian Plugin]
    end

    OBSIDIAN --> API
    REFBOOKS --> API
    BLOG --> API
    API --> EMBED
    EMBED --> VDB
    API --> LLM
    API --> CELERY
    CELERY --> REDIS
    WEB --> API
    PLUGIN --> API
```

### Celery Background Task System

이 시스템은 **Celery**를 사용하여 비동기 백그라운드 작업을 처리합니다:

- **비동기 검증 작업**: 대용량 토픽 검증을 백그라운드에서 처리
- **진행 상황 추적**: 실시간 작업 상태 모니터링
- **결과 캐싱**: Redis 기반 결과 캐싱으로 성능 최적화
- **동기/비동기 호환**: Celery worker 내부에서 동기 세션 사용

#### 아키텍처 특징

- **FastAPI + Celery**: REST API와 백그라운드 작업 분리
- **Redis Broker**: 메시지 브로커 및 결과 백엔드로 사용
- **Sync Session Pattern**: Celery worker에서 동기 DB 세션 사용으로 트랜잭션 문제 해결

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 22+
- Docker & Docker Compose
- Obsidian (optional)

### Installation

1. **Clone repository:**
```bash
git clone <repository-url>
cd itpe-topic-enhancement
```

2. **Start services:**
```bash
docker-compose up -d redis chromadb
```

3. **Backend setup:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env  # Edit configuration
```

4. **Frontend setup:**
```bash
cd frontend
npm install
cp .env.example .env
```

5. **Run applications:**
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

6. **Access application:**
- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Usage

### 1. Export Topics from Obsidian

기존 Dataview JSON 내보내기 스크립트를 사용하여 토픽 추출:

```javascript
// Dataview 스크립트 실행 후
// "JSON 내보내기 (전체)" 버튼 클릭
// 클립보드에 복사된 JSON 저장
```

### 2. Upload to System

Web UI 또는 API를 통해 토픽 업로드:

```bash
curl -X POST http://localhost:8000/api/v1/topics/upload \
  -H "Content-Type: application/json" \
  -d @topics.json
```

### 3. Validate Topics

검증 요청:

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"topic_ids": ["topic-001", "topic-002"]}'
```

### 4. Review Proposals

Web UI에서 검증 결과 확인 및 제안 적용:

1. Dashboard에서 진행 상황 확인
2. Validation Results에서 상세 내용 확인
3. Proposals에서 우선순위별 제안 검토
4. Apply 버튼으로 마크다운 파일 업데이트

## Documentation

- **[System Design](DESIGN.md)**: 전체 시스템 설계
- **[Technology Stack](TECH_STACK.md)**: 기술 스택 상세
- **[Project Structure](PROJECT_STRUCTURE.md)**: 프로젝트 구조
- **[API Documentation](http://localhost:8000/docs)**: OpenAPI/Swagger (실행 중일 때)
- **[Backend README](backend/README.md)**: 백엔드 설정 및 트랜잭션 관리 가이드
- **[Background Task Transaction Management](.moai/docs/background-task-transaction-management.md)**: 백그라운드 작업 트랜잭션 관리 패턴

### Recent Updates

**2026-02-04**: 토픽 레벨 의미적 유사도 기반 키워드 추출 (SPEC-KEYWORD-SIM-001)

**문제점 해결:** 기존 도메인 레벨 키워드 추출이 너무 광범위하여 모든 SW 주제가 동일한 키워드를 반환했습니다. 예를 들어 "객체지향" 관련 주제가 "SW 품질" 관련 키워드를 받았습니다.

**개선 사항:**

- **토픽별 의미적 키워드 추출**: `POST /api/v1/keywords/suggest-by-topic` API 추가
  - 주제의 콘텐츠(정의, 리드문, 키워드)를 분석하여 의미적으로 관련된 키워드 추천
  - 코사인 유사도 기반 매칭 (임계값 필터링 지원)
  - 데이터 소스: 600제, 서브노트

- **새로운 API 사용 예시:**
```bash
curl -X POST http://localhost:8000/api/v1/keywords/suggest-by-topic \
  -H "Content-Type: application/json" \
  -d '{
    "topic_id": "abc-123",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

- **핵심 컴포넌트:**
  - `KeywordMatch`: 키워드 매칭 결과 데이터 클래스
  - `KeywordEmbeddingRepository`: 키워드 임베딩 인메모리 캐시
  - `SemanticKeywordService`: 토픽 기반 키워드 추천 서비스

- **테스트 커버리지:**
  - 17개 단위 테스트
  - 9개 통합 테스트
  - 기존 131개 테스트 모두 통과
  - **총 157/157 테스트 통과**

자세한 내용: [CHANGELOG.md](CHANGELOG.md), [SPEC-KEYWORD-SIM-001](.moai/specs/SPEC-KEYWORD-SIM-001/spec.md)

**2026-02-04**: P0 우선순위 버그 수정 (SPEC-FIX-P0)

- **P0-KEYWORD**: 키워드 제안 엔드포인트가 실제 데이터 소스에서 키워드 추출
  - `GET /api/v1/keywords/suggest?domain=SW&top_k=10`
  - 데이터 소스: 600제, 서브노트
  - 복합어 보존, 동의어 확장, 불용어 필터링 지원

- **P0-LLM**: LLM 파이프라인 실제 연동
  - OpenAI Client 구현 (`app/services/llm/openai.py`)
  - Validation Engine에 LLM 통합
  - 캐싱 (24시간 TTL) 및 fallback 메커니즘
  - 환경 설정: `llm_provider`, `openai_model`, `ollama_model`

- **P0-METRICS**: 메트릭 수집 시스템 통합
  - MetricsMiddleware 구현 (자동 성능 수집)
  - `GET /api/v1/metrics/summary` 엔드포인트
  - 키워드 관련성, 참조 발견율, 검증 정확도, 시스템 성능 메트릭

자세한 내용: [CHANGELOG.md](CHANGELOG.md), [SPEC-FIX-P0](.moai/specs/SPEC-FIX-P0/spec.md)

**2026-02-04**: 백그라운드 검증 작업 트랜잭션 커밋 문제 수정 (SPEC-FIX-001)

- 문제: 백그라운드 검증 작업이 완료되지만 데이터베이스에 결과가 저장되지 않음
- 수정: `async_session()` 사용 시 명시적 `await db.commit()` 추가
- 영향: 검증 결과가 올바르게 데이터베이스에 저장됨
- 자세한 내용: [SPEC-FIX-001](.moai/specs/SPEC-FIX-001/spec.md)

## Configuration

### Backend (.env)

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/itpe-enhancement.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Vector DB
CHROMADB_PATH=./data/chromadb

# LLM (OpenAI)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.3

# Embedding
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MPNet-base-v2
EMBEDDING_DEVICE=cuda  # or cpu

# Obsidian
OBSIDIAN_VAULT_PATH=/path/to/obsidian/vault
```

### Frontend (.env)

```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=ITPE Topic Enhancement
```

## Development

### Backend Development

```bash
cd backend

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Format code
ruff format app/
ruff check app/

# Type check
mypy app/
```

### Frontend Development

```bash
cd frontend

# Run dev server
npm run dev

# Run tests
npm run test

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

## Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Production Deployment

1. **Configure systemd service:**
```bash
sudo cp scripts/itpe-enhancement.service /etc/systemd/system/
sudo systemctl enable itpe-enhancement
sudo systemctl start itpe-enhancement
```

2. **Configure nginx:**
```bash
sudo cp nginx.conf /etc/nginx/sites-available/itpe-enhancement
sudo ln -s /etc/nginx/sites-available/itpe-enhancement /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Roadmap

### Phase 1: MVP (Conservative) - 2-3 weeks
- [ ] PDF/Markdown parser
- [ ] Keyword-based matching
- [ ] Basic validation rules
- [ ] Simple web UI

### Phase 2: Core (Balanced) - 4-5 weeks
- [ ] Embedding-based matching
- [ ] LLM proposal generation
- [ ] Advanced validation rules
- [ ] Full-featured UI
- [ ] Obsidian plugin

### Phase 3: Advanced (Aggressive) - 3-4 weeks
- [ ] RAG pipeline
- [ ] Local LLM support
- [ ] Feedback learning
- [ ] Performance optimization

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** support@example.com

## Acknowledgments

- FB21 수험서 저자님
- 블로그 참조 (https://blog.skby.net)
- Obsidian 커뮤니티

---

**Version:** 1.0.0
**Status:** Design Phase
**Last Updated:** 2026-02-02
