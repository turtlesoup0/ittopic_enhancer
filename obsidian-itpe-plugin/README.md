# ITPE Topic Enhancement Obsidian Plugin

ITPE Topic Enhancement System과 Obsidian을 통합하여 토픽 내용을 검증하고 개선 제안을 받습니다.

## 기능

### 1. Dataview JSON 내보내기
- Dataview 쿼리 실행 결과를 JSON 포맷으로 변환
- 클립보드에 복사 또는 파일로 저장
- ITPE Topic Enhancement API 호환 형식

### 2. 동기화 기능
- 로컬 마크다운 파일 스캔
- 백엔드 API로 토픽 업로드
- 검증 결과 가져오기
- 제안 내용을 마크다운에 적용

### 3. 설정 관리
- API 엔드포인트 설정
- API 키 입력
- 동기화 주기 설정
- 도메인 매핑 설정

## 설치

### 개발 모드

1. 저장소 클론:
```bash
git clone https://github.com/turtlesoup0/itpe-topic-enhancement.git
cd itpe-topic-enhancement/obsidian-itpe-plugin
```

2. 의존성 설치:
```bash
npm install
```

3. 빌드:
```bash
npm run build
```

4. Obsidian에 플러그인 로드:
- Obsidian 설정 → 플러그인 → 개발자 모드 활성화
- "폴더에서 찾아보기"로 이 저장소 선택

## 사용법

### 1. 초기 설정

1. Obsidian 설정에서 "ITPE Topic Enhancement" 탭 열기
2. API 엔드포인트 설정 (기본값: `http://localhost:8000/api/v1`)
3. 필요한 경우 API 키 입력
4. 도메인 매핑 확인

### 2. Dataview JSON 내보내기

명령 팔레트 (Ctrl/Cmd + P)에서 "Dataview JSON 내보내기" 실행:
- 현재 파일의 Dataview 쿼리 결과를 JSON으로 변환
- 클립보드에 복사
- `itpe-topics.json` 파일로 저장

### 3. 토픽 동기화

#### 현재 파일 동기화
- 명령 팔레트에서 "현재 파일 동기화" 실행
- 또는 파일 우클릭 → "ITPE로 동기화"

#### 전체 토픽 동기화
- 명령 팔레트에서 "전체 토픽 동기화" 실행
- 모든 마크다운 파일에서 토픽 추출
- 백엔드로 업로드 후 검증 요청

### 4. 제안 확인 및 적용

#### 제안 보기
- 명령 팔레트에서 "제안 보기" 실행
- 새 노트에 제안 목록 생성

#### 제안 적용
- 명령 팔레트에서 "제안 적용" 실행
- 제안 내용이 파일에 자동 적용

### 5. 자동 동기화

설정에서 자동 동기화 활성화:
- 지정된 간격으로 자동 동기화
- 기본값: 60분

## API 통합

### 사용되는 엔드포인트

- `GET /api/v1/health` - 연결 테스트
- `POST /api/v1/validate` - 검증 요청
- `GET /api/v1/validate/task/{task_id}` - 상태 조회
- `GET /api/v1/validate/task/{task_id}/result` - 결과 조회
- `POST /api/v1/validate/task/{task_id}/proposals` - 제안 생성
- `GET /api/v1/proposals?topic_id={id}` - 제안 목록
- `POST /api/v1/proposals/apply` - 제안 적용
- `POST /api/v1/proposals/{id}/reject` - 제안 거절

## 개발

### 프로젝트 구조

```
obsidian-itpe-plugin/
├── main.ts           # 플러그인 메인
├── settings.ts       # 설정 탭
├── sync.ts           # 동기화 기능
├── export.ts         # Dataview JSON 내보내기
├── types.ts          # 타입 정의
├── manifest.json     # Obsidian 플러그인 매니페스트
├── package.json      # NPM 의존성
├── tsconfig.json     # TypeScript 설정
├── esbuild.config.mjs # 빌드 설정
└── README.md         # 이 파일
```

### 빌드 명령

```bash
# 개발 모드 (파일 변경 감지)
npm run dev

# 프로덕션 빌드
npm run build

# 버전 업
npm run version
```

## 의존성

- Obsidian API
- Dataview 플러그인 (선택 사항, 권장)

## 라이선스

MIT

## 저자

turtlesoup0

## 버전

1.0.0
