/**
 * ITPE Topic Enhancement System 타입 정의
 * 백엔드 API 모델과 호환되는 타입
 */

/** 도메인 열거형 */
export enum DomainEnum {
	신기술 = "신기술",
	정보보안 = "정보보안",
	네트워크 = "네트워크",
	데이터베이스 = "데이터베이스",
	SW = "SW",
	프로젝트관리 = "프로젝트관리"
}

/** 출제 빈도 열거형 */
export enum ExamFrequencyEnum {
	HIGH = "high",
	MEDIUM = "medium",
	LOW = "low"
}

/** 토픽 메타데이터 */
export interface TopicMetadata {
	file_path: string;
	file_name: string;
	folder: string;
	domain: DomainEnum;
	exam_frequency: ExamFrequencyEnum;
}

/** 토픽 내용 */
export interface TopicContent {
	리드문: string;
	정의: string;
	키워드: string[];
	해시태그: string;
	암기: string;
}

/** 필드 완성도 */
export interface TopicCompletionStatus {
	리드문: boolean;
	정의: boolean;
	키워드: boolean;
	해시태그: boolean;
	암기: boolean;
}

/** 토픽 전체 모델 */
export interface Topic {
	id: string;
	metadata: TopicMetadata;
	content: TopicContent;
	completion: TopicCompletionStatus;
	embedding?: number[];
	last_validated?: string;
	validation_score?: number;
	created_at: string;
	updated_at: string;
}

/** 검증 요청 */
export interface ValidationRequest {
	topic_ids: string[];
	domain_filter?: string;
}

/** 검증 응답 */
export interface ValidationResponse {
	task_id: string;
	status: string;
	estimated_time: number;
}

/** 검증 작업 상태 */
export interface ValidationTaskStatus {
	task_id: string;
	status: string;
	progress?: number;
	current?: number;
	total?: number;
	error?: string;
}

/** 갭 유형 */
export enum GapType {
	MISSING_FIELD = "missing_field",
	INCOMPLETE_DEFINITION = "incomplete_definition",
	INSUFFICIENT_KEYWORDS = "insufficient_keywords",
	OUTDATED_CONTENT = "outdated_content",
	INACCURATE_CONTENT = "inaccurate_content"
}

/** 제안 우선순위 */
export enum ProposalPriority {
	CRITICAL = "critical",
	HIGH = "high",
	MEDIUM = "medium",
	LOW = "low"
}

/** 개선 제안 */
export interface EnhancementProposal {
	id: string;
	topic_id: string;
	title: string;
	description: string;
	gap_type: GapType;
	priority: ProposalPriority;
	target_field: keyof TopicContent;
	original_content: string;
	suggested_content: string;
	references: string[];
	confidence_score: number;
	is_applied: boolean;
	is_rejected: boolean;
	created_at: string;
}

/** 제안 목록 응답 */
export interface ProposalListResponse {
	proposals: EnhancementProposal[];
	total: number;
	topic_id: string;
}

/** 제안 적용 요청 */
export interface ProposalApplyRequest {
	proposal_id: string;
	topic_id: string;
}

/** 제안 적용 응답 */
export interface ProposalApplyResponse {
	success: boolean;
	message: string;
	updated_content: string;
}

/** Dataview 쿼리 결과 (Obsidian 내부) */
export interface DataviewQueryResult {
	성공: boolean;
	데이터: Topic[];
	에러?: string;
}

/** 플러그인 설정 */
export interface ITPEPluginSettings {
	apiEndpoint: string;
	apiKey: string;
	syncInterval: number; // 분 단위
	domainMapping: Record<string, DomainEnum>;
	autoSync: boolean;
	notificationsEnabled: boolean;
}

/** 기본 설정 */
export const DEFAULT_SETTINGS: ITPEPluginSettings = {
	apiEndpoint: "http://localhost:8000/api/v1",
	apiKey: "",
	syncInterval: 60,
	domainMapping: {
		"1_신기술": DomainEnum.신기술,
		"2_정보보안": DomainEnum.정보보안,
		"3_네트워크": DomainEnum.네트워크,
		"4_데이터베이스": DomainEnum.데이터베이스,
		"5_SW": DomainEnum.SW,
		"9_알고리즘_자료구조": DomainEnum.SW,
		"8_프로젝트관리": DomainEnum.프로젝트관리
	},
	autoSync: false,
	notificationsEnabled: true
};
