# ITPE Topic Enhancement - Frontend

정보관리기술사 시험 준비를 위한 토픽 검증 및 보강 제안 시스템 프론트엔드.

## 기술 스택

- **React 19** - UI 라이브러리
- **TypeScript 5.9** - 타입 안전성
- **Vite 6.0** - 빌드 도구
- **shadcn/ui** - UI 컴포넌트 라이브러리
- **Zustand** - 상태 관리
- **Recharts** - 차트 라이브러리
- **Tailwind CSS** - 스타일링

## 시작하기

### 사전 요구사항

- Node.js 22+
- npm 또는 yarn 또는 pnpm

### 설치

\`\`\`bash
npm install
\`\`\`

### 개발 서버 실행

\`\`\`bash
npm run dev
\`\`\`

브라우저에서 [http://localhost:3000](http://localhost:3000)을 열어 확인하세요.

### 빌드

\`\`\`bash
npm run build
\`\`\`

### 프리뷰

\`\`\`bash
npm run preview
\`\`\`

## 프로젝트 구조

\`\`\`
frontend/
├── src/
│   ├── app/                 # 앱 라우트 (Next.js App Router 사용 시)
│   ├── components/          # React 컴포넌트
│   │   ├── ui/             # shadcn/ui 기본 컴포넌트
│   │   ├── dashboard/      # 대시보드 컴포넌트
│   │   ├── topics/         # 토픽 관련 컴포넌트
│   │   ├── validation/     # 검증 관련 컴포넌트
│   │   └── proposals/      # 제안 관련 컴포넌트
│   ├── lib/                # 유틸리티 및 API 클라이언트
│   ├── types/              # TypeScript 타입 정의
│   └── styles/             # 전역 스타일
├── public/                 # 정적 assets
├── index.html              # HTML 진입점
├── package.json            # 의존성 및 스크립트
├── tsconfig.json           # TypeScript 설정
├── vite.config.ts          # Vite 설정
└── tailwind.config.js      # Tailwind CSS 설정
\`\`\`

## 주요 기능

1. **대시보드** - 전체 통계 및 진행 현황
2. **토픽 목록** - 도메인별 필터링, 검색, 완성도 표시
3. **검증 결과** - Before/After 비교, 보강 필요 항목 표시
4. **제안 관리** - 우선순위별 제안 목록, 적용/거절 기능

## API 연동

백엔드 API는 `http://localhost:8000`에서 실행 중이어야 합니다.

환경 변수를 통해 API URL을 설정할 수 있습니다:

\`\`\`env
VITE_API_BASE_URL=http://localhost:8000/api/v1
\`\`\`

## 라이선스

MIT
