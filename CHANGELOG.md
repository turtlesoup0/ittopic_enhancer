# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### 토픽 레벨 의미적 유사도 기반 키워드 추출 (SPEC-KEYWORD-SIM-001)

도메인 레벨 접근 방식의 한계를 극복하기 위해 토픽별 의미적 유사도 기반 키워드 추출 시스템을 구현했습니다.

**문제점:**
- 모든 SW 주제가 동일한 키워드 세트를 반환
- "객체지향" 주제가 "SW 품질" 관련 키워드를 수신
- 토픽 콘텐츠와 키워드 간의 의미적 관련성 부족

**해결 방안:**

- **SemanticKeywordService**: 토픽 콘텐츠(정의, 리드문, 키워드)를 기반으로 의미적 유사도 계산
- **KeywordEmbeddingRepository**: 키워드 임베딩 인메모리 캐시로 빠른 유사도 검색
- **KeywordMatch**: 키워드, 유사도 점수, 출처를 포함한 매칭 결과

**주요 변경사항:**
- `app/services/keywords/similarity_extractor.py` - 의미적 키워드 추출 서비스
- `app/services/keywords/__init__.py` - 서비스 모듈 초기화
- `app/api/v1/endpoints/keywords.py` - `POST /api/v1/keywords/suggest-by-topic` 엔드포인트

**API 사용 예시:**
```bash
# 토픽별 의미적 키워드 추천
POST /api/v1/keywords/suggest-by-topic
Content-Type: application/json

{
  "topic_id": "abc-123",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "topic_id": "abc-123",
    "keywords": [
      {"keyword": "캡슐화", "similarity": 0.92, "source": "600제_SW_120회"},
      {"keyword": "상속", "similarity": 0.89, "source": "서브노트_SW_OOP"},
      {"keyword": "다형성", "similarity": 0.87, "source": "600제_SW_125회"}
    ],
    "count": 3
  }
}
```

**테스트:**
- `tests/unit/test_similarity_extractor.py` - 단위 테스트 (17개)
- `tests/integration/test_semantic_keywords_api.py` - 통합 테스트 (9개)
- 총 157/157 테스트 통과

**주요 특징:**
- 코사인 유사도 기반 매칭
- 유사도 임계값 필터링 (기본값: 0.7)
- 키워드 임베딩 사전 계산으로 성능 최적화
- 기존 도메인 레벨 API와 호환 유지

**Breaking Changes:**
- 없음 (새로운 API 추가)

**참고:**
- 자세한 내용은 `.moai/specs/SPEC-KEYWORD-SIM-001/`을 참조하세요

#### P0 우선순위 버그 수정 (SPEC-FIX-P0)

SPEC-REVIEW-001에서 식별된 3개의 P0 우선순위 이슈를 해결하여 시스템의 핵심 기능을 완성했습니다.

**P0-KEYWORD: 실제 키워드 추출 구현**

키워드 제안 엔드포인트가 placeholder 텍스트 대신 실제 데이터 소스에서 키워드를 추출합니다.

**주요 변경사항:**
- **KeywordExtractor 서비스**: `app/services/matching/keyword_extractor.py` - 복합어 보존, 동의어 확장, 불용어 필터링
- **키워드 제안 API**: `app/api/v1/endpoints/keywords.py` - `GET /api/v1/keywords/suggest`
- **데이터 소스 통합**: 600제, 서브노트에서 텍스트 수집 및 추출
- **도메인 필터링**: SW, NW, DB, 정보보안, 신기술, 경영, 기타 도메인별 키워드 추출 지원

**API 사용 예시:**
```bash
# 모든 도메인 상위 10개 키워드
GET /api/v1/keywords/suggest

# SW 도메인 상위 20개 키워드
GET /api/v1/keywords/suggest?domain=SW&top_k=20
```

**영향을 받는 파일:**
- `backend/app/api/v1/endpoints/keywords.py` - 키워드 제안 엔드포인트
- `backend/app/services/matching/keyword_extractor.py` - 키워드 추출 서비스
- `backend/config/synonyms.yaml` - 동의어 매핑
- `backend/config/stopwords.yaml` - 불용어 설정

**P0-LLM: LLM 파이프라인 연동**

LLM 파이프라인이 실제로 호출되도록 구현하여 Validation Engine에서 LLM 기반 검증을 수행합니다.

**주요 변경사항:**
- **OpenAI Client**: `app/services/llm/openai.py` - OpenAI API 클라이언트 구현
- **LLM 통합**: Validation Engine에 LLM 호출 연결
- **캐싱 메커니즘**: LLM 응답 24시간 캐싱으로 비용 절감
- **Fallback 지원**: LLM 호출 실패 시 rule-based 검증으로 graceful degradation

**환경 설정 (`.env`):**
```bash
# LLM 제공자 선택 (openai 또는 ollama)
LLM_PROVIDER=openai

# OpenAI 설정
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# LLM 파라미터
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000
```

**영향을 받는 파일:**
- `backend/app/services/llm/openai.py` - OpenAI 클라이언트
- `backend/app/core/env_config.py` - LLM 설정 추가
- `backend/app/services/validation/engine.py` - LLM 통합 (기존 파일 수정)

**P0-METRICS: 메트릭 수집 통합**

메트릭 모듈을 API와 통합하여 모든 요청의 성능 메트릭을 자동으로 수집합니다.

**주요 변경사항:**
- **MetricsMiddleware**: `app/core/middleware.py` - 모든 API 요청의 응답 시간과 성공/실패 자동 수집
- **메트릭 요약 엔드포인트**: `app/api/v1/endpoints/metrics.py` - `GET /api/v1/metrics/summary`
- **미들웨어 등록**: `app/main.py`에 MetricsMiddleware 등록

**메트릭 카테고리:**
- **keyword_relevance**: 키워드 관련성 (Precision, Recall, F1)
- **reference_discovery**: 참조 문서 발견율, 커버리지율, 유사도
- **validation_accuracy**: 검증 정확도
- **system_performance**: API 응답 시간, 성공률

**API 사용 예시:**
```bash
# 모든 메트릭 요약 조회
GET /api/v1/metrics/summary
```

**영향을 받는 파일:**
- `backend/app/core/middleware.py` - MetricsMiddleware 추가
- `backend/app/api/v1/endpoints/metrics.py` - 메트릭 요약 엔드포인트
- `backend/app/main.py` - 미들웨어 등록

**Breaking Changes:**
- 없음 (새로운 기능 추가)

**참고:**
- 자세한 내용은 `.moai/specs/SPEC-FIX-P0/`을 참조하세요

#### Celery 비동기 검증 시스템 (SPEC-CELERY-001)

#### Celery 비동기 검증 시스템 (SPEC-CELERY-001)

백그라운드 검증 작업 처리를 위해 Celery 기반 비동기 시스템을 도입했습니다.

**주요 변경사항:**
- **Celery Worker 구현**: `app/services/llm/worker.py` - 비동기 검증 작업 처리
- **동기 레포지토리 계층**: `app/db/repositories/*_sync.py` - Celery worker용 동기 DB 접근
- **Sync 래퍼**: `app/services/sync_wrapper.py` - 비동기 함수를 동기 컨텍스트에서 실행
- **환경 설정**: `app/core/env_config.py` - Celery 브로커/백엔드 URL 설정
- **마크다운 파서 개선**: `app/services/parser/markdown_parser.py` - 하위 노트 분할 기능 강화

**영향을 받는 파일:**
- `backend/app/db/session.py` - SyncSessionLocal 추가
- `backend/app/db/repositories/topic_sync.py` - 새로운 동기 토픽 레포지토리
- `backend/app/db/repositories/validation_sync.py` - 새로운 동기 검증 레포지토리
- `backend/app/services/llm/worker.py` - Celery worker 구현
- `backend/app/services/sync_wrapper.py` - 동기 래퍼 구현
- `backend/app/core/env_config.py` - Celery 설정 추가
- `backend/pyproject.toml` - psycopg2-binary 의존성 추가
- `backend/app/core/middleware.py` - 로거 섀도잉 버그 수정

**테스트:**
- `tests/integration/test_validation_celery_characterization.py` - Celery 검증 동작 테스트
- `tests/unit/test_celery_validation_api.py` - Celery API 단위 테스트
- `tests/unit/test_markdown_parser.py` - 마크다운 파서 단위 테스트

**참고:**
- Celery worker는 별도의 프로세스에서 실행되며 Redis를 브로커로 사용합니다
- Worker 내부에서는 동기 DB 세션을 사용하여 이벤트 루프 충돌을 방지합니다
- 자세한 내용은 `.moai/specs/SPEC-CELERY-001/`을 참조하세요

### Changed

#### Async/Sync 호환성 개선 (SPEC-BGFIX-002)

Celery worker 내부에서 비동기 함수 호출 시 발생하는 이벤트 루프 충돌 문제를 해결했습니다.

**문제 설명:**
- Celery worker는 별도의 프로세스에서 실행되며 자체 이벤트 루프를 가집니다
- 기존 비동기 레포지토리를 직접 사용할 때 "no running event loop" 오류 발생

**수정 내용:**
- Celery worker 내부에서 사용할 동기 레포지토리 계층 (`*_sync.py`) 생성
- `SyncSessionLocal` 세션 팩토리 추가로 동기 트랜잭션 지원
- `run_sync()` 래퍼 함수로 비동기 함수를 동기 컨텍스트에서 실행

**영향을 받는 파일:**
- `backend/app/db/session.py` - SyncSessionLocal 추가
- `backend/app/db/repositories/topic_sync.py` - 동기 토픽 레포지토리
- `backend/app/db/repositories/validation_sync.py` - 동기 검증 레포지토리
- `backend/app/services/sync_wrapper.py` - 동기 래퍼

### Fixed

#### 백그라운드 검증 작업 트랜잭션 커밋 누락 문제 (SPEC-FIX-001)

**문제 설명:**
백그라운드 검증 작업이 완료되지만 데이터베이스에 결과가 저장되지 않는 문제가 있었습니다. 이는 `async_session()` 컨텍스트 매니저가 자동 커밋을 수행하지 않기 때문에 발생했습니다.

**수정 내용:**
- `backend/app/api/v1/endpoints/validation.py`의 `_process_validation` 함수에 명시적 `await db.commit()` 호출 추가
- 성공 경로: 검증 결과 저장 후 명시적 커밋으로 데이터 영구 저장 보장
- 실패 경로: 에러 발생 시 새로운 세션에서 실패 상태 저장 후 명시적 커밋
- 트랜잭션 관리 패턴을 문서화하는 docstring 추가
- Event loop 관리를 위한 wrapper 함수 추가

**영향을 받는 파일:**
- `backend/app/api/v1/endpoints/validation.py` - 트랜잭션 커밋 추가, docstring 개선
- `backend/tests/integration/test_validation_transaction.py` - 트랜잭션 동작 검증 테스트 추가

**테스트:**
- 백그라운드 작업 완료 후 검증 결과가 데이터베이스에 저장되는지 확인
- 작업 실패 시 실패 상태와 에러 메시지가 올바르게 저장되는지 확인
- Characterization test를 통해 수정 전/후 동작 차이 문서화

**참고:**
- 백그라운드 작업은 별도의 event loop에서 실행되므로 세션 라이프사이클 관리가 중요합니다
- 리포지토리 계층은 `flush()`만 수행하며, 커밋은 서비스/엔드포인트 계층의 책임입니다
- 자세한 내용은 `.moai/specs/SPEC-FIX-001/`을 참조하세요

---

## [1.0.0] - 2026-02-02

### Added
- ITPE Topic Enhancement System 초기 구현
- FastAPI 백엔드 API
- React 프론트엔드 대시보드
- Obsidian Plugin 기본 기능
- 토픽 검증 시스템
- 참조 문서 매칭 서비스
- LLM 기반 제안 생성

### Features
- PDF/Markdown 파서
- 키워드 기반 매칭
- 기본 검증 규칙
- 웹 UI
- RESTful API

---

[Unreleased]: https://github.com/your-org/itpe-topic-enhancement/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/itpe-topic-enhancement/releases/tag/v1.0.0
