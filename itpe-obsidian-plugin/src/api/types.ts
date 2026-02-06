/**
 * API 타입 정의 - ITPE Obsidian Plugin
 *
 * 백엔드 API 모델과 일치하는 TypeScript 인터페이스 정의
 */

// ============================================================================
// 도메인 enum
// ============================================================================

/**
 * 토픽 도메인 enum
 */
export enum DomainEnum {
	SW = "SW",
	정보보안 = "정보보안",
	신기술 = "신기술",
	네트워크 = "네트워크",
	데이터베이스 = "데이터베이스",
}

/**
 * 콘텐츠 격차 유형 enum
 */
export enum GapType {
	INCOMPLETE_DEFINITION = "incomplete_definition",
	MISSING_EXAMPLES = "missing_examples",
	WEAK_KEYWORDS = "weak_keywords",
	INSUFFICIENT_DEPTH = "insufficient_depth",
}

/**
 * 참고소스 유형 enum
 */
export enum ReferenceSourceType {
	PDF_BOOK = "pdf_book",
	WEB_ARTICLE = "web_article",
	TECHNICAL_DOC = "technical_doc",
}

/**
 * 제안 우선순위 enum
 */
export enum ProposalPriority {
	CRITICAL = "critical",
	HIGH = "high",
	MEDIUM = "medium",
	LOW = "low",
}

/**
 * 작업 상태 enum
 */
export enum TaskStatus {
	PENDING = "pending",
	PROCESSING = "processing",
	COMPLETED = "completed",
	FAILED = "failed",
}

// ============================================================================
// Topic 모델
// ============================================================================

/**
 * 토픽 메타데이터
 */
export interface TopicMetadata {
	file_path: string;
	file_name: string;
	folder: string;
	domain: DomainEnum;
}

/**
 * 토픽 콘텐츠
 */
export interface TopicContent {
	리드문: string;
	정의: string;
	키워드: string[];
	해시태그: string;
	암기: string;
}

/**
 * 토픽 완료 상태
 */
export interface TopicCompletionStatus {
	리드문: boolean;
	정의: boolean;
	키워드: boolean;
	해시태그: boolean;
	암기: boolean;
}

/**
 * 토픽 전체 구조
 */
export interface Topic {
	id: string;
	metadata: TopicMetadata;
	content: TopicContent;
	completion: TopicCompletionStatus;
}

// ============================================================================
// Validation 모델
// ============================================================================

/**
 * 콘텐츠 격차 (Content Gap)
 */
export interface ContentGap {
	gap_type: GapType;
	field_name: string;
	current_value: string;
	suggested_value: string;
	confidence: number;
	reference_id: string;
	reasoning: string;
}

/**
 * 매칭된 참고자료
 */
export interface MatchedReference {
	reference_id: string;
	title: string;
	source_type: ReferenceSourceType;
	similarity_score: number;
	domain: string;
	trust_score: number;
	relevant_snippet: string;
}

/**
 * 검증 결과
 */
export interface ValidationResult {
	id: string;
	topic_id: string;
	overall_score: number;
	field_completeness_score: number;
	content_accuracy_score: number;
	reference_coverage_score: number;
	gaps: ContentGap[];
	matched_references: MatchedReference[];
	validation_timestamp: string;
}

// ============================================================================
// Proposal 모델
// ============================================================================

/**
 * 향상 제안
 */
export interface EnhancementProposal {
	id: string;
	topic_id: string;
	priority: ProposalPriority;
	title: string;
	description: string;
	current_content: string;
	suggested_content: string;
	reasoning: string;
	reference_sources: string[];
	estimated_effort: number; // minutes
	confidence: number;
	created_at: string;
	/** 대상 필드 (title과 동일한 의미, 호환성용) */
	target_field?: string;
}

// ============================================================================
// API Request/Response 타입
// ============================================================================

/**
 * 토픽 업로드 요청
 */
export interface UploadTopicsRequest {
	topics: Topic[];
}

/**
 * 토픽 업로드 응답
 */
export interface UploadTopicsResponse {
	uploaded: number;
	topic_ids: string[];
	/** 실패한 토픽 수 (선택적) */
	failed?: number;
}

/**
 * 검증 작업 생성 요청
 */
export interface CreateValidationRequest {
	topic_ids: string[];
}

/**
 * 검증 작업 생성 응답
 */
export interface CreateValidationResponse {
	task_id: string;
	status: string;
}

/**
 * 작업 상태 응답
 */
export interface TaskStatusResponse {
	id: string;
	status: TaskStatus;
	created_at: string;
	completed_at?: string;
}

/**
 * 제안 조회 요청 파라미터
 */
export interface GetProposalsRequest {
	topic_id?: string;
	priority?: ProposalPriority;
	limit?: number;
}

/**
 * 제안 조회 응답
 */
export interface GetProposalsResponse {
	proposals: EnhancementProposal[];
	total: number;
}

/**
 * 토픽 업데이트 요청
 */
export interface UpdateTopicRequest {
	metadata?: Partial<TopicMetadata>;
	content?: Partial<TopicContent>;
}

/**
 * 토픽 업데이트 응답
 */
export interface UpdateTopicResponse {
	id: string;
	updated: boolean;
}

// ============================================================================
// 에러 타입
// ============================================================================

/**
 * API 에러 응답
 */
export interface APIErrorResponse {
	detail: string;
	status_code?: number;
	error_code?: string;
}

// ============================================================================
// 클라이언트 설정
// ============================================================================

/**
 * API 클라이언트 설정
 */
export interface ITPEApiClientConfig {
	baseUrl: string;
	apiKey: string;
	timeout?: number;
	maxRetries?: number;
}

// ============================================================================
// 플러그인 설정 타입
// ============================================================================

/**
 * ITPE 플러그인 설정 인터페이스
 */
export interface ITPEPluginSettings {
	backendUrl: string;           // 백엔드 API URL
	apiKey: string;               // API 키
	autoSync: boolean;            // 자동 동기화
	syncInterval: number;         // 동기화 간격 (분)
	showStatusBar: boolean;       // 상태 표시줄 표시
	debugMode: boolean;           // 디버그 모드
	domainFolders: string[];      // 도메인 폴더 경로 목록
}

/**
 * 기본 설정 값
 */
export const DEFAULT_SETTINGS: ITPEPluginSettings = {
	backendUrl: "http://localhost:8000",
	apiKey: "",
	autoSync: false,
	syncInterval: 5,
	showStatusBar: true,
	debugMode: false,
	domainFolders: ["SW", "정보보안", "신기술", "네트워크", "데이터베이스"],
};
