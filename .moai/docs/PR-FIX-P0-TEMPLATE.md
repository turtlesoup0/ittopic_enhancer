# Pull Request: SPEC-FIX-P0 - P0 우선순위 버그 수정

## Summary

SPEC-REVIEW-001에서 식별된 3개의 P0 우선순위 이슈를 해결하여 시스템의 핵심 기능을 완성합니다.

### Fixed Issues

1. **P0-KEYWORD**: 키워드 제안 엔드포인트가 실제 데이터 소스에서 키워드를 추출하도록 구현
2. **P0-LLM**: LLM 파이프라인을 실제로 연동하여 Validation Engine에서 LLM 기반 검증 수행
3. **P0-METRICS**: 메트릭 모듈을 API와 통합하여 자동 메트릭 수집 구현

## Changes

### P0-KEYWORD: 키워드 추출 구현

**New Files:**
- `backend/app/api/v1/endpoints/keywords.py` - 키워드 제안 API 엔드포인트
- `backend/app/services/matching/keyword_extractor.py` - 키워드 추출 서비스

**Features:**
- 데이터 소스(600제, 서브노트)에서 실제 키워드 추출
- 복합어 보존 정규식 (TCP/IP, REST API 등 분리 방지)
- 동의어 확장 기능
- 불용어 필터링
- 도메인별 필터링 (SW, NW, DB, 정보보안, 신기술, 경영, 기타)

**API Endpoint:**
```http
GET /api/v1/keywords/suggest?domain=SW&top_k=10
```

### P0-LLM: LLM 파이프라인 연동

**New Files:**
- `backend/app/services/llm/openai.py` - OpenAI 클라이언트

**Modified Files:**
- `backend/app/core/env_config.py` - LLM 설정 추가

**Features:**
- OpenAI API 클라이언트 구현
- Validation Engine에 LLM 통합
- 24시간 LLM 응답 캐싱
- LLM 호출 실패 시 fallback 메커니즘
- JSON 형식 응답 지원

**Configuration:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000
```

### P0-METRICS: 메트릭 수집 통합

**New Files:**
- `backend/app/api/v1/endpoints/metrics.py` - 메트릭 요약 엔드포인트

**Modified Files:**
- `backend/app/core/middleware.py` - MetricsMiddleware 추가

**Features:**
- 모든 API 요청의 응답 시간과 성공/실패 자동 수집
- 키워드 관련성, 참조 발견율, 검증 정확도, 시스템 성능 메트릭

**API Endpoint:**
```http
GET /api/v1/metrics/summary
```

## Testing

### Manual Testing

**1. 키워드 추출 테스트:**
```bash
# 모든 도메인 키워드
curl "http://localhost:8000/api/v1/keywords/suggest"

# SW 도메인 키워드 (20개)
curl "http://localhost:8000/api/v1/keywords/suggest?domain=SW&top_k=20"
```

**2. 메트릭 요약 테스트:**
```bash
curl "http://localhost:8000/api/v1/metrics/summary"
```

**3. LLM 검증 테스트:**
```bash
# 검증 요청 (LLM provider 설정 필요)
curl -X POST "http://localhost:8000/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{"topic_ids": ["test-topic-001"]}'
```

### Expected Results

1. 키워드 추출: 실제 데이터 소스에서 추출된 키워드 목록 반환
2. 메트릭 요약: 모든 메트릭 카테고리의 요약된 데이터 반환
3. LLM 검증: OpenAI API 호출 후 검증 결과 반환 (API key 설정 시)

## Breaking Changes

**없음** - 새로운 기능만 추가되었습니다.

## Documentation

- [SPEC-FIX-P0](../specs/SPEC-FIX-P0/spec.md) - 상세 명세서
- [CHANGELOG.md](../../CHANGELOG.md) - 변경 로그
- [backend/README.md](../../backend/README.md) - API 엔드포인트 문서

## Checklist

- [x] 코드가 테스트되었습니다
- [x] 문서가 업데이트되었습니다
- [x] CHANGELOG.md에 항목이 추가되었습니다
- [x] Breaking changes가 문서화되었습니다 (해당 사항 없음)

## Related Issues

- Resolves SPEC-REVIEW-001 P0 issues
