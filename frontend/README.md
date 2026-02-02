# ITPE Topic Enhancement - Frontend

정보관리기술사 시험 준비를 위한 토픽 검증 및 보강 제안 시스템 프론트엔드.

## 기술 스택

- **React 19** - UI 라이브러리
- **TypeScript 5.9** - 타입 안전성
- **Vite 6.0** - 빌드 도구
- **React Router v7** - 라우팅
- **shadcn/ui** - UI 컴포넌트 라이브러리
- **Zustand** - 상태 관리
- **TanStack Query** - 서버 상태 관리
- **Recharts** - 차트 라이브러리
- **Tailwind CSS** - 스타일링

## 시작하기

### 사전 요구사항

- Node.js 22+
- npm 또는 yarn 또는 pnpm
- 백엔드 API 서버 실행 (http://localhost:8000)

### 설치

```bash
npm install
```

### 개발 서버 실행

```bash
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열어 확인하세요.

### 빌드

```bash
npm run build
```

### 프리뷰

```bash
npm run preview
```

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/          # React 컴포넌트
│   │   ├── ui/             # shadcn/ui 기본 컴포넌트
│   │   ├── layout/         # 레이아웃 컴포넌트 (Header, Sidebar)
│   │   ├── dashboard/      # 대시보드 컴포넌트
│   │   ├── topics/         # 토픽 관련 컴포넌트
│   │   ├── validation/     # 검증 관련 컴포넌트
│   │   └── proposals/      # 제안 관련 컴포넌트
│   ├── pages/              # 페이지 컴포넌트
│   │   ├── DashboardPage.tsx
│   │   ├── TopicsPage.tsx
│   │   ├── ValidationPage.tsx
│   │   └── ProposalsPage.tsx
│   ├── lib/                # 유틸리티 및 API 클라이언트
│   │   ├── api.ts          # Axios API 클라이언트
│   │   ├── store.ts        # Zustand 스토어
│   │   └── utils.ts        # 유틸리티 함수
│   ├── types/              # TypeScript 타입 정의
│   │   └── api.ts          # API 관련 타입
│   ├── App.tsx             # 앱 진입점
│   ├── main.tsx            # React 마운트
│   └── globals.css         # 전역 스타일
├── public/                 # 정적 assets
├── index.html              # HTML 진입점
├── package.json            # 의존성 및 스크립트
├── tsconfig.json           # TypeScript 설정
├── vite.config.ts          # Vite 설정
├── tailwind.config.js      # Tailwind CSS 설정
└── components.json         # shadcn/ui 설정
```

## 주요 기능

### 1. 대시보드 (/)
- 전체 토픽 통계 (총 토픽, 완성된 토픽, 검증된 토픽, 평균 완성률)
- 도메인별 현황 차트
- 최근 검증된 토픽 목록
- 빠른 작업 바로가기

### 2. 토픽 관리 (/topics)
- 토픽 업로드 (JSON 파일 또는 직접 입력)
- 토픽 목록 테이블 (도메인 필터링, 검색)
- 토픽 상세 보기 (내용, 메타데이터, 상태)
- 일괄 검증 요청

### 3. 검증 (/validation)
- 토픽 선택 및 검증 요청
- 실시간 진행률 표시
- 검증 결과 상세 보기
- 보강 항목 및 참조 문서 확인

### 4. 제안 (/proposals)
- 우선순위별 제안 목록
- 상태별 필터링 (대기 중, 적용 완료, 거절됨)
- 제안 상세 보기 (현재/제안 내용 비교)
- 제안 적용/거절 기능

## API 연동

백엔드 API는 Vite 프록시를 통해 연결됩니다:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

환경 변수를 통해 API URL을 설정할 수 있습니다:

```env
# .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_API_KEY=your-api-key-here
```

## UI 컴포넌트

shadcn/ui 기반 컴포넌트:

- Button, Input, Label, Select, Tabs, Dialog, Table, Badge, Progress, Card, Toast
- Checkbox (추가)

## 스토어

Zustand를 사용한 상태 관리:

- `useAppStore`: 사이드바 상태, 선택된 도메인
- `useValidationStore`: 검증 태스크 ID, 결과

## 반응형 디자인

- 모바일: 320px+
- 태블릿: 768px+
- 데스크톱: 1024px+

모든 페이지와 컴포넌트는 반응형으로 설계되었습니다.

## 한국어 지원

모든 UI 텍스트는 한국어로 제공됩니다.

## 라이선스

MIT
