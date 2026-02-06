/**
 * Backend API 클라이언트 - ITPE Obsidian Plugin
 *
 * 재시도 로직, 타임아웃, 타입 안전한 API 호출을 제공하는 견고한 HTTP 클라이언트
 */
import type {
	UploadTopicsRequest,
	UploadTopicsResponse,
	CreateValidationRequest,
	CreateValidationResponse,
	TaskStatusResponse,
	ValidationResult,
	GetProposalsRequest,
	GetProposalsResponse,
	UpdateTopicRequest,
	UpdateTopicResponse,
	ITPEApiClientConfig,
	APIErrorResponse,
} from "./types";
import { Logger } from "../utils/logger";

// ============================================================================
// 에러 클래스
// ============================================================================

/**
 * API 에러 - HTTP 응답 에러
 */
export class APIError extends Error {
	constructor(
		message: string,
		public statusCode: number,
		public response?: unknown,
	) {
		super(message);
		this.name = "APIError";
	}
}

/**
 * 네트워크 에러 - 연결 실패
 */
export class NetworkError extends Error {
	constructor(message: string, public cause?: Error) {
		super(message);
		this.name = "NetworkError";
	}
}

/**
 * 타임아웃 에러
 */
export class TimeoutError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "TimeoutError";
	}
}

// ============================================================================
// API 클라이언트
// ============================================================================

/**
 * ITPE Backend API 클라이언트
 *
 * @example
 * ```typescript
 * const client = new ITPEApiClient({
 *   baseUrl: "http://localhost:8000",
 *   apiKey: "your-api-key",
 *   timeout: 30000,
 *   maxRetries: 3
 * });
 *
 * const result = await client.uploadTopics({ topics: [...] });
 * ```
 */
export class ITPEApiClient {
	private config: ITPEApiClientConfig;
	private logger: Logger;

	/**
	 * API 클라이언트 생성자
	 *
	 * @param config - 클라이언트 설정
	 * @param logger - 로거 인스턴스
	 */
	constructor(config: ITPEApiClientConfig, logger: Logger) {
		this.config = {
			timeout: 30000, // 30초 기본 타임아웃
			maxRetries: 3, // 기본 최대 재시도 횟수
			...config,
		};
		this.logger = logger;
	}

	// ========================================================================
	// API 메서드
	// ========================================================================

	/**
	 * 토픽 업로드
	 *
	 * POST /api/v1/topics/upload
	 *
	 * @param request - 토픽 업로드 요청
	 * @returns 업로드된 토픽 정보
	 */
	async uploadTopics(request: UploadTopicsRequest): Promise<UploadTopicsResponse> {
		this.logger.api("POST", "/api/v1/topics/upload", request);
		return this.request<UploadTopicsResponse>("POST", "/api/v1/topics/upload", request);
	}

	/**
	 * 검증 작업 생성
	 *
	 * POST /api/v1/validate/
	 *
	 * @param request - 검증 작업 생성 요청
	 * @returns 생성된 작업 정보
	 */
	async createValidation(request: CreateValidationRequest): Promise<CreateValidationResponse> {
		this.logger.api("POST", "/api/v1/validate/", request);
		return this.request<CreateValidationResponse>("POST", "/api/v1/validate/", request);
	}

	/**
	 * 작업 상태 조회
	 *
	 * GET /api/v1/validate/task/{id}
	 *
	 * @param taskId - 작업 ID
	 * @returns 작업 상태
	 */
	async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
		this.logger.api("GET", `/api/v1/validate/task/${taskId}`);
		return this.request<TaskStatusResponse>("GET", `/api/v1/validate/task/${taskId}`);
	}

	/**
	 * 검증 결과 조회
	 *
	 * GET /api/v1/validate/task/{id}/result
	 *
	 * @param taskId - 작업 ID
	 * @returns 검증 결과
	 */
	async getValidationResult(taskId: string): Promise<ValidationResult> {
		this.logger.api("GET", `/api/v1/validate/task/${taskId}/result`);
		return this.request<ValidationResult>("GET", `/api/v1/validate/task/${taskId}/result`);
	}

	/**
	 * 향상 제안 조회
	 *
	 * GET /api/v1/proposals
	 *
	 * @param params - 조회 파라미터 (선택)
	 * @returns 제안 목록
	 */
	async getProposals(params?: GetProposalsRequest): Promise<GetProposalsResponse> {
		const queryParams = new URLSearchParams();
		if (params?.topic_id) {
			queryParams.append("topic_id", params.topic_id);
		}
		if (params?.priority) {
			queryParams.append("priority", params.priority);
		}
		if (params?.limit) {
			queryParams.append("limit", params.limit.toString());
		}

		const queryString = queryParams.toString();
		const path = `/api/v1/proposals${queryString ? `?${queryString}` : ""}`;

		this.logger.api("GET", path, params);
		return this.request<GetProposalsResponse>("GET", path);
	}

	/**
	 * 토픽 업데이트
	 *
	 * PATCH /api/v1/topics/{id}
	 *
	 * @param topicId - 토픽 ID
	 * @param request - 업데이트 요청
	 * @returns 업데이트 결과
	 */
	async updateTopic(topicId: string, request: UpdateTopicRequest): Promise<UpdateTopicResponse> {
		this.logger.api("PATCH", `/api/v1/topics/${topicId}`, request);
		return this.request<UpdateTopicResponse>("PATCH", `/api/v1/topics/${topicId}`, request);
	}

	/**
	 * API 연결 테스트
	 *
	 * @returns 연결 성공 여부
	 */
	async testConnection(): Promise<boolean> {
		try {
			await this.request<GetProposalsResponse>("GET", "/api/v1/proposals?limit=1");
			this.logger.info("API 연결 테스트 성공");
			return true;
		} catch (error) {
			this.logger.error("API 연결 테스트 실패", error);
			return false;
		}
	}

	// ========================================================================
	// 내부 헬퍼 메서드
	// ========================================================================

	/**
	 * 재시도 로직이 포함된 HTTP 요청
	 *
	 * @param method - HTTP 메서드
	 * @param path - API 경로
	 * @param body - 요청 바디 (선택)
	 * @returns 응답 데이터
	 */
	private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
		const maxRetries = this.config.maxRetries ?? 3;
		let lastError: Error | undefined;

		for (let attempt = 0; attempt <= maxRetries; attempt++) {
			try {
				return await this.fetchWithTimeout<T>(method, path, body);
			} catch (error) {
				lastError = error as Error;

				// 재시도하지 않을 에러 경우
				if (error instanceof APIError) {
					// 4xx 에러는 재시도하지 않음 (클라이언트 에러)
					if (error.statusCode >= 400 && error.statusCode < 500) {
						throw error;
					}
				}

				// 마지막 시도면 에러를 �짐
				if (attempt === maxRetries) {
					this.logger.error(`요청 실패 (시도 ${attempt + 1}/${maxRetries + 1})`, error);
					throw lastError;
				}

				// 지수 백오프로 대기
				const delay = this.calculateBackoffDelay(attempt);
				this.logger.warn(`요청 실패, ${delay}ms 후 재시도 (${attempt + 1}/${maxRetries})`, error);
				await this.sleep(delay);
			}
		}

		throw lastError ?? new NetworkError("알 수 없는 네트워크 에러");
	}

	/**
	 * 타임아웃이 포함된 fetch 요청
	 *
	 * @param method - HTTP 메서드
	 * @param path - API 경로
	 * @param body - 요청 바디 (선택)
	 * @returns 응답 데이터
	 */
	private async fetchWithTimeout<T>(method: string, path: string, body?: unknown): Promise<T> {
		const url = `${this.config.baseUrl}${path}`;
		const timeout = this.config.timeout ?? 30000;

		// AbortController로 타임아웃 구현
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		try {
			const response = await fetch(url, {
				method,
				headers: this.getHeaders(),
				body: body ? JSON.stringify(body) : undefined,
				signal: controller.signal,
			});

			clearTimeout(timeoutId);
			return await this.handleResponse<T>(response);
		} catch (error) {
			clearTimeout(timeoutId);

			// AbortError를 TimeoutError로 변환
			if (error instanceof Error && error.name === "AbortError") {
				throw new TimeoutError(`요청 타임아웃 (${timeout}ms)`);
			}

			// 네트워크 에러 처리
			if (error instanceof TypeError) {
				throw new NetworkError("네트워크 연결 실패", error);
			}

			throw error;
		}
	}

	/**
	 * 응답 처리 및 에러 변환
	 *
	 * @param response - Fetch 응답
	 * @returns 파싱된 응답 데이터
	 */
	private async handleResponse<T>(response: Response): Promise<T> {
		if (!response.ok) {
			let errorData: APIErrorResponse = {
				detail: response.statusText,
				status_code: response.status,
			};

			try {
				const data = await response.json();
				errorData = { ...errorData, ...data };
			} catch {
				// JSON 파싱 실패 시 기본 에러 메시지 사용
			}

			throw new APIError(errorData.detail, response.status, errorData);
		}

		return response.json() as Promise<T>;
	}

	/**
	 * 요청 헤더 생성
	 *
	 * @returns HTTP 헤더
	 */
	private getHeaders(): HeadersInit {
		const headers: HeadersInit = {
			"Content-Type": "application/json",
			Accept: "application/json",
		};

		if (this.config.apiKey) {
			headers["X-API-Key"] = this.config.apiKey;
		}

		return headers;
	}

	/**
	 * 지수 백오프 대기 시간 계산
	 *
	 * @param attempt - 시도 횟수 (0-based)
	 * @returns 대기 시간 (ms)
	 */
	private calculateBackoffDelay(attempt: number): number {
		// 기본 백오프: 2^attempt * 1000ms (1s, 2s, 4s, 8s, ...)
		// 최대 대기 시간: 10초
		const baseDelay = Math.pow(2, attempt) * 1000;
		const maxDelay = 10000;
		return Math.min(baseDelay, maxDelay);
	}

	/**
	 * 지정된 시간 동안 대기
	 *
	 * @param ms - 대기 시간 (밀리초)
	 * @returns Promise
	 */
	private sleep(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}

// ============================================================================
// 유틸리티 타입
// ============================================================================

/**
 * API 에러 타입 가드
 *
 * @param error - 에러 객체
 * @returns APIError 여부
 */
export function isAPIError(error: unknown): error is APIError {
	return error instanceof APIError;
}

/**
 * 네트워크 에러 타입 가드
 *
 * @param error - 에러 객체
 * @returns NetworkError 여부
 */
export function isNetworkError(error: unknown): error is NetworkError {
	return error instanceof NetworkError;
}

/**
 * 타임아웃 에러 타입 가드
 *
 * @param error - 에러 객체
 * @returns TimeoutError 여부
 */
export function isTimeoutError(error: unknown): error is TimeoutError {
	return error instanceof TimeoutError;
}
