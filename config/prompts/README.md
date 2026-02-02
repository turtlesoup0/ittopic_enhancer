# ITPE Topic Enhancement Prompts

도메인별 LLM 프롬프트 최적화 시스템

## 구조

```
config/prompts/
├── validation/           # 검증(Validation) 프롬프트
│   ├── ai_tech.txt      # 신기술 (AI, ML, Cloud)
│   ├── security.txt     # 정보보안
│   ├── network.txt      # 네트워크
│   ├── database.txt     # 데이터베이스
│   ├── software.txt     # 소프트웨어 공학
│   ├── embedded.txt     # 임베디드 시스템
│   ├── project_management.txt  # 프로젝트 관리
│   ├── os.txt           # 운영체제
│   └── ecommerce.txt    # 전자상거래
├── proposals/           # 제안(Proposal) 프롬프트
│   ├── ai_tech.txt      # 신기술
│   ├── security.txt     # 정보보안
│   ├── network.txt      # 네트워크
│   ├── database.txt     # 데이터베이스
│   ├── software.txt     # 소프트웨어 공학
│   ├── embedded.txt     # 임베디드 시스템
│   ├── project_management.txt  # 프로젝트 관리
│   ├── os.txt           # 운영체제
│   └── ecommerce.txt    # 전자상거래
├── validation_system.txt # 통합 시스템 프롬프트
└── proposal_system.txt  # 통합 제안 프롬프트
```

## 도메인별 특화 사항

### 1. 신기술 (ai_tech)
**검증 중점:**
- 수학적 기초 (선형대수, 확률, 미적분)
- 알고리즘 상세 (구조, 파라미터, 복잡도)
- 성능 지표 (정확도, 정밀도, 재현율, F1)
- 비교 분석 (전통 방식 vs 새로운 기술)
- 실제 적용 사례

**제안 중점:**
- 수식 추가 (비용 함수, 그라디언트)
- 아키텍처 다이어그램
- 프레임워크 예시 (TensorFlow, PyTorch)
- 윤리적 고려사항

### 2. 정보보안 (security)
**검증 중점:**
- CIA 트라이어드 관련성
- 알고리즘 사양 (키 길이, 블록 크기)
- 위협 모델 및 완화
- 표준 준수 (ISO 27001, NIST, PCI DSS)
- 대안과의 비교

**제안 중점:**
- 보안 목적 명시
- 공격 시나리오
- 표준 준수 요구사항
- 구현 가이드

### 3. 네트워크 (network)
**검증 중점:**
- OSI 7계층 위치
- PDU 타입
- 헤더 구조
- 표준 참조 (RFC, IEEE)
- 포트 번호

**제안 중점:**
- 계층 위치 명시
- 헤더 필드 상세
- 동작 흐름도
- 유사 프로토콜 비교

### 4. 데이터베이스 (database)
**검증 중점:**
- 수학적 기초 (함수적 종속)
- 정규형 정의
- SQL 예시
- ERD/다이어그램
- 성능 고려사항

**제안 중점:**
- 함수적 종속 표기
- 정규화 단계별 예시
- SQL 쿼리와 결과
- 반정규화 비교

### 5. 소프트웨어 공학 (software)
**검증 중점:**
- 프로세스 정의
- 역할과 책임
- 산출물 및 작업물
- UML 다이어그램
- 장단점 비교

**제안 중점:**
- 단계별 프로세스
- 입출력 기준
- 산출물 템플릿
- 실무 적용 사례

### 6. 임베디드 시스템 (embedded)
**검증 중점:**
- 아키텍처 다이어그램
- 레지스터/메모리 맵
- 타이밍 명세
- 코드 예시
- 전력 소비

**제안 중점:**
- 블록 다이어그램
- 레지스터 정의
- 펌웨어 코드
- GPOS 비교

### 7. 프로젝트 관리 (project_management)
**검증 중점:**
- 수식과 계산
- 판정 기준
- 프로세스 단계
- 도구와 기법
- 계산 예시

**제안 중점:**
- 공식과 해석
- 임계값 기준
- 작업 예제
- 베스트 프랙티스

### 8. 운영체제 (os)
**검증 중점:**
- 알고리즘 상세
- 데이터 구조 (PCB, 페이지 테이블)
- 상태 전이도
- 계산 예시
- 실제 OS 구현

**제안 중점:**
- 알고리즘 단계
- 복잡도 분석
- 상태 다이어그램
- 비교 분석

### 9. 전자상거래 (ecommerce)
**검증 중점:**
- 프로세스 흐름
- 보안 메커니즘
- 수수료 구조
- 법적 규정
- 서비스 예시

**제안 중점:**
- 단계별 흐름도
- PG vs VAN 구분
- 보안 요구사항
- 법적 준비사항

## 사용 방법

### 검증(Validation) 사용
```python
# 프롬프트 로드
with open('config/prompts/validation/ai_tech.txt', 'r') as f:
    validation_prompt = f.read()

# LLM에 전달
response = llm.complete(
    validation_prompt,
    topic_content=topic_content,
    reference_materials=references
)
```

### 제안(Proposal) 사용
```python
# 프롬프트 로드
with open('config/prompts/proposals/ai_tech.txt', 'r') as f:
    proposal_prompt = f.read()

# LLM에 전달
response = llm.complete(
    proposal_prompt,
    topic_content=topic_content,
    reference_materials=references
)
```

## 버전 관리

- **v1.0.0** (2025-01-03): 초기 9개 도메인 프롬프트 작성
  - 검증 프롬프트: 9개
  - 제안 프롬프트: 9개
  - 총 18개 도메인별 프롬프트

## 평가 기준

성공 기준:
- [x] 9개 도메인별 검증 프롬프트 작성
- [x] 9개 도메인별 제안 프롬프트 작성
- [x] 도메인별 전문 용어 포함
- [x] 구체적인 예시 포함
- [x] 출력 형식 준수 (JSON)
- [x] 한글 및 영문 지원

## 향후 개선

1. **A/B 테스트 지원**: 각 프롬프트의 변형 생성
2. **피드백 루프**: 사용자 피드백 반영
3. **자동 평가**: 프롬프트 품질 자동 측정
4. **멀티모달**: 이미지/다이어그램 입력 지원
