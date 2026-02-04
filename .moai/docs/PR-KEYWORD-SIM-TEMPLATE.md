# Pull Request Template: SPEC-KEYWORD-SIM-001

## 제목: 토픽별 의미적 유사도 기반 키워드 추출 구현

## 개요

도메인 레벨 키워드 추출의 한계를 극복하기 위해 토픽별 의미적 유사도 기반 키워드 추출 시스템을 구현했습니다. 이를 통해 각 토픽의 실제 콘텐츠와 관련된 키워드를 제공할 수 있게 되었습니다.

## 문제점

### 이전 접근 방식의 한계

- **도메인 레벨 추출**: 모든 SW 토픽이 동일한 키워드 세트를 반환
- **의미적 관련성 부족**: "객체지향" 주제가 "SW 품질" 관련 키워드를 수신
- **사용자 경험 저하**: 토픽과 관련 없는 키워드로 인한 혼란

### 예시

```
# 이전: 도메인 레벨 API
GET /api/v1/keywords/suggest?domain=SW

# 모든 SW 토픽에 대해 동일한 결과:
["REST API", "TCP/IP", "데이터베이스", "알고리즘", "소프트웨어 공학"]

# 문제: "객체지향 프로그래밍" 주제에 부적절한 키워드
```

## 해결 방안

### 새로운 API 엔드포인트

```http
POST /api/v1/keywords/suggest-by-topic
Content-Type: application/json

{
  "topic_id": "abc-123",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

### 응답

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

## 구현 상세

### 핵심 컴포넌트

#### 1. KeywordMatch (데이터 클래스)

```python
class KeywordMatch:
    """키워드 매칭 결과."""
    keyword: str          # 키워드
    similarity: float     # 유사성 점수 (0.0 ~ 1.0)
    source: str          # 출처 문서
```

#### 2. KeywordEmbeddingRepository (저장소)

- 키워드 임베딩 인메모리 캐시
- 코사인 유사도 기반 검색
- 임계값 필터링

#### 3. SemanticKeywordService (서비스)

- 토픽 콘텐츠 임베딩 생성
- 참조 문서에서 키워드 추출 및 인덱싱
- 의미적 유사도 계산

### 파일 변경사항

**新增 파일:**
- `backend/app/services/keywords/similarity_extractor.py` - 의미적 키워드 추출 서비스
- `backend/app/services/keywords/__init__.py` - 서비스 모듈 초기화
- `backend/tests/unit/test_similarity_extractor.py` - 단위 테스트 (17개)
- `backend/tests/integration/test_semantic_keywords_api.py` - 통합 테스트 (9개)

**변경 파일:**
- `backend/app/api/v1/endpoints/keywords.py` - 새로운 엔드포인트 추가

## Before/After 비교

### Before: 도메인 레벨

```bash
# 객체지향 주제에 대한 키워드 요청
GET /api/v1/keywords/suggest?domain=SW

# 결과:
["REST API", "TCP/IP", "데이터베이스", "알고리즘", "소프트웨어 공학"]
```

### After: 토픽 레벨

```bash
# 객체지향 주제에 대한 키워드 요청
POST /api/v1/keywords/suggest-by-topic
{"topic_id": "oop-001", "top_k": 5}

# 결과:
[
  {"keyword": "캡슐화", "similarity": 0.92, "source": "600제_SW_120회"},
  {"keyword": "상속", "similarity": 0.89, "source": "서브노트_SW_OOP"},
  {"keyword": "다형성", "similarity": 0.87, "source": "600제_SW_125회"},
  {"keyword": "추상화", "similarity": 0.85, "source": "기출_SW_2023"},
  {"keyword": "인터페이스", "similarity": 0.82, "source": "서브노트_SW_OOP"}
]
```

## 테스트 결과

### 테스트 커버리지

- **단위 테스트**: 17개 통과
- **통합 테스트**: 9개 통과
- **기존 테스트**: 131개 통과
- **총계**: 157/157 통과 (100%)

### 테스트 파일

- `tests/unit/test_similarity_extractor.py`
  - KeywordMatch 생성 및 변환
  - KeywordEmbeddingRepository 키워드 관리
  - SemanticKeywordService 초기화 및 추천

- `tests/integration/test_semantic_keywords_api.py`
  - API 엔드포인트 동작 확인
  - 토픽 조회 및 응답 형식 검증
  - 유사도 임계값 필터링 확인

## 호환성

### Breaking Changes

- **없음**: 새로운 API 엔드포인트 추가
- 기존 `GET /api/v1/keywords/suggest` 엔드포인트 유지

### Backward Compatibility

- 기존 도메인 레벨 API 계속 지원
- 새로운 토픽 레벨 API와 병행 사용 가능

## 배포 확인사항

- [ ] 토픽 콘텐츠(정의, 리드문, 키워드)가 데이터베이스에 존재
- [ ] 데이터 소스 경로(600제, 서브노트)가 올바르게 설정
- [ ] 임베딩 모델이 로드되고 초기화 완료
- [ ] API 엔드포인트가 정상적으로 응답

## 관련 문서

- [SPEC-KEYWORD-SIM-001](../specs/SPEC-KEYWORD-SIM-001/spec.md) - 상세 사양서
- [backend/README.md](../../backend/README.md) - API 문서
- [CHANGELOG.md](../../CHANGELOG.md) - 변경 기록

## 검토자 확인사항

- [ ] API 설계가 적절한지
- [ ] 테스트 커버리지가 충분한지
- [ ] 문서가 최신화되었는지
- [ ] 호환성 문제가 없는지

---

**SPEC ID**: SPEC-KEYWORD-SIM-001
**작성일**: 2026-02-04
**상태**: 구현 완료, 검토 대기
