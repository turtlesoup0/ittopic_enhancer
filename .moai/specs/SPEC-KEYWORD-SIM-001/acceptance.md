# SPEC-KEYWORD-SIM-001: 인수 기준

## TAG BLOCK

```
SPEC-ID: SPEC-KEYWORD-SIM-001
Document: acceptance.md
Version: 1.0
Created: 2026-02-04
```

## 정의 (Definition of Done)

- [ ] 모든 EARS 요구사항이 구현됨
- [ ] 모든 테스트 시나리오가 통과함
- [ ] LSP 에러가 없음 (type errors, lint errors)
- [ ] 단위 테스트 커버리지 85% 이상
- [ ] API 문서가 완료됨
- [ ] 성능 목표(500ms)가 충족됨

## 테스트 시나리오

### ACC-SIM-001: 주제 콘텐츠 임베딩 생성

**Given** 주제 ID가 "abc-123"이고 주제가 다음과 같을 때:
```
리드문: 객체지향 프로그래밍의 핵심 개념
정의: 캡슐화, 상속, 다형성, 추상화
키워드: ["OOP", "클래스", "객체"]
```

**When** `prepare_topic_text()`를 호출하면

**Then** 다음 텍스트가 반환되어야 한다:
```
"객체지향 프로그래밍의 핵심 개념 캡슐화, 상속, 다형성, 추상화 OOP 클래스 객체"
```

**And** `encode_async()`를 호출하면 768차원 임베딩 벡터가 반환되어야 한다

### ACC-SIM-002: 참조 문서 키워드 추출

**Given** 참조 문서가 다음과 같을 때:
```
도메인: SW
제목: 객체지향 프로그래밍 기초
콘텐츠: "캡슐화는 데이터를 보호하는 기술이다. 상속은 코드를 재사용한다..."
```

**When** `initialize_from_references()`를 호출하면

**Then** 다음 키워드가 추출되어야 한다:
- "캡슐화"
- "상속"
- "데이터"
- "코드"
- "재사용"

**And** 각 키워드에 대한 임베딩이 생성되어야 한다

**And** 각 키워드의 출처가 저장되어야 한다

### ACC-SIM-003: 의미 유사성 계산

**Given** 주제 임베딩이 "객체지향 프로그래밍"에 대한 것일 때

**And** 다음 키워드 임베딩이 저장되어 있을 때:
- "캡슐화" (유사성: 0.92)
- "상속" (유사성: 0.89)
- "다형성" (유사성: 0.87)
- "추상화" (유사성: 0.85)
- "네트워크" (유사성: 0.45)

**When** `find_similar(topic_embedding, top_k=3, threshold=0.7)`를 호출하면

**Then** 다음 결과가 반환되어야 한다:
```python
[
    {"keyword": "캡슐화", "similarity": 0.92, "source": "..."},
    {"keyword": "상속", "similarity": 0.89, "source": "..."},
    {"keyword": "다형성", "similarity": 0.87, "source": "..."}
]
```

**And** "네트워크"는 임계값 미만으로 제외되어야 한다

### ACC-SIM-004: API 엔드포인트 동작

**Given** 애플리케이션이 시작되고 키워드가 인덱싱되었을 때

**When** 다음 요청을 보내면:
```http
POST /api/v1/keywords/suggest-by-topic
Content-Type: application/json

{
  "topic_id": "abc-123",
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**Then** 다음 응답이 반환되어야 한다:
```json
{
  "success": true,
  "data": {
    "keywords": [
      {"keyword": "캡슐화", "similarity": 0.92, "source": "600제_SW_120회"},
      {"keyword": "상속", "similarity": 0.89, "source": "서브노트_SW_OOP"},
      {"keyword": "다형성", "similarity": 0.87, "source": "600제_SW_125회"},
      {"keyword": "추상화", "similarity": 0.85, "source": "기출_SW_2023"}
    ],
    "count": 4
  },
  "request_id": "...",
  "timestamp": "..."
}
```

**And** HTTP 상태 코드는 200이어야 한다

### ACC-SIM-005: 성능 기준 (NFR-SIM-001)

**Given** 키워드가 1000개 인덱싱되어 있을 때

**When** 주제 기반 키워드 추천 API를 호출하면

**Then** 응답 시간이 500ms 이내여야 한다

**And** 캐시 히트 시 100ms 이내여야 한다

### ACC-SIM-006: 정확도 기준 (NFR-SIM-002)

**Given** "객체지향 프로그래밍" 주제일 때

**When** 상위 5개 키워드 추천을 요청하면

**Then** 다음 OOP 관련 키워드가 최소 4개 포함되어야 한다:
- 캡슐화
- 상속
- 다형성
- 추상화
- 클래스

**And** 관련 없는 키워드(예: "네트워크", "TCP/IP")는 포함되지 않아야 한다

### ACC-SIM-007: 에러 처리

**Given** 애플리케이션이 실행 중일 때

**When** 존재하지 않는 topic_id로 요청하면:
```json
{
  "topic_id": "non-existent-id"
}
```

**Then** 다음 에러 응답이 반환되어야 한다:
```json
{
  "success": false,
  "message": "주제를 찾을 수 없습니다.",
  "details": {"topic_id": "non-existent-id"},
  "request_id": "...",
  "timestamp": "..."
}
```

**And** HTTP 상태 코드는 404이어야 한다

### ACC-SIM-008: 파라미터 검증

**Given** 애플리케이션이 실행 중일 때

**When** 잘못된 파라미터로 요청하면:
```json
{
  "topic_id": "abc-123",
  "top_k": 100,  // 최대값 초과
  "similarity_threshold": 1.5  // 범위 초과
}
```

**Then** 다음 검증 에러 응답이 반환되어야 한다:
```json
{
  "success": false,
  "message": "파라미터 검증 실패",
  "details": {
    "top_k": "1에서 20 사이여야 합니다",
    "similarity_threshold": "0.0에서 1.0 사이여야 합니다"
  }
}
```

**And** HTTP 상태 코드는 422이어야 한다

### ACC-SIM-009: 캐싱 동작

**Given** 동일한 주제에 대해 첫 번째 요청이 처리되었을 때

**When** 같은 주제로 두 번째 요청을 보내면

**Then** 응답 시간이 100ms 이내여야 한다 (캐시 히트)

**And** 반환된 키워드가 첫 번째 요청과 동일해야 한다

### ACC-SIM-010: 초기화 상태 확인

**Given** 애플리케이션이 시작될 때

**When** 키워드 인덱싱이 완료되면

**Then** 로그에 다음 메시지가 출력되어야 있다:
```
INFO: semantic_keywords_initialized: 500 keywords indexed
```

**And** 인덱싱된 키워드 수가 0보다 커야 한다

## 품질 게이트 확인 목록

### TRUST 5 프레임워크

**Tested**:
- [ ] 단위 테스트 커버리지 85% 이상
- [ ] 모든 테스트 시나리오 통과

**Readable**:
- [ ] 명확한 함수/변수 명명
- [ ] 한국어 주석
- [ ] ruff lint 통과

**Unified**:
- [ ] black 포맷팅 통과
- [ ] 일관된 코드 스타일

**Secured**:
- [ ] 입력 검증 (topic_id, top_k, similarity_threshold)
- [ ] SQL 인젝션 방지
- [ ] 에러 메시지에 민감 정보 노출 방지

**Trackable**:
- [ ] 커밋 메시지에 SPEC-ID 참조
- [ ] 로그에 요청 ID 포함
