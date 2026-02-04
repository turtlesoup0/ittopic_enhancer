# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
