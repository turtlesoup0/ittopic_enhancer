import { Notice } from "obsidian";
import ITPEPlugin from "./main";
import {
	Topic,
	ValidationRequest,
	ValidationResponse,
	ValidationTaskStatus,
	ValidationResult,
	EnhancementProposal,
	ProposalListResponse,
	ProposalApplyRequest,
	ProposalApplyResponse,
} from "./types";

/**
 * 동기화 기능
 * 로컬 마크다운 파일을 백엔드 API로 업로드하고 검증 결과를 가져옵니다.
 */
export class SyncManager {
	plugin: ITPEPlugin;

	constructor(plugin: ITPEPlugin) {
		this.plugin = plugin;
	}

	/**
	 * API 연결 테스트
	 */
	async testConnection(): Promise<boolean> {
		const url = `${this.plugin.settings.apiEndpoint}/health`;

		try {
			const response = await fetch(url, {
				method: "GET",
				headers: this.getHeaders(),
			});

			if (response.ok) {
				const data = await response.json();
				return data.status === "healthy";
			}

			return false;
		} catch (error) {
			console.error("API 연결 테스트 실패:", error);
			return false;
		}
	}

	/**
	 * 토픽들을 백엔드로 업로드하고 검증을 요청합니다.
	 */
	async uploadTopics(topics: Topic[]): Promise<ValidationResponse> {
		const url = `${this.plugin.settings.apiEndpoint}/validate`;

		const request: ValidationRequest = {
			topic_ids: topics.map((t) => t.id),
		};

		try {
			const response = await fetch(url, {
				method: "POST",
				headers: this.getHeaders(),
				body: JSON.stringify(request),
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "업로드 실패");
			}

			const data = await response.json();

			new Notice(`검증 요청 완료: ${topics.length}개 토픽`);

			return data;
		} catch (error) {
			new Notice(`업로드 실패: ${error}`);
			throw error;
		}
	}

	/**
	 * 검증 작업 상태를 조회합니다.
	 */
	async getValidationStatus(taskId: string): Promise<ValidationTaskStatus> {
		const url = `${this.plugin.settings.apiEndpoint}/validate/task/${taskId}`;

		try {
			const response = await fetch(url, {
				method: "GET",
				headers: this.getHeaders(),
			});

			if (!response.ok) {
				throw new Error("상태 조회 실패");
			}

			return await response.json();
		} catch (error) {
			console.error("상태 조회 실패:", error);
			throw error;
		}
	}

	/**
	 * 검증 결과를 가져옵니다.
	 */
	async getValidationResults(taskId: string): Promise<ValidationResult[]> {
		const url = `${this.plugin.settings.apiEndpoint}/validate/task/${taskId}/result`;

		try {
			const response = await fetch(url, {
				method: "GET",
				headers: this.getHeaders(),
			});

			if (!response.ok) {
				throw new Error("검증 결과 조회 실패");
			}

			return await response.json();
		} catch (error) {
			console.error("검증 결과 조회 실패:", error);
			throw error;
		}
	}

	/**
	 * 검증 작업에 대한 제안들을 생성합니다.
	 */
	async generateProposals(taskId: string): Promise<EnhancementProposal[]> {
		const url = `${this.plugin.settings.apiEndpoint}/validate/task/${taskId}/proposals`;

		try {
			const response = await fetch(url, {
				method: "POST",
				headers: this.getHeaders(),
			});

			if (!response.ok) {
				throw new Error("제안 생성 실패");
			}

			const proposals = await response.json();

			new Notice(`${proposals.length}개의 제안이 생성되었습니다.`);

			return proposals;
		} catch (error) {
			new Notice(`제안 생성 실패: ${error}`);
			throw error;
		}
	}

	/**
	 * 토픽에 대한 제안 목록을 가져옵니다.
	 */
	async getProposals(topicId: string): Promise<ProposalListResponse> {
		const url = `${this.plugin.settings.apiEndpoint}/proposals?topic_id=${topicId}`;

		try {
			const response = await fetch(url, {
				method: "GET",
				headers: this.getHeaders(),
			});

			if (!response.ok) {
				throw new Error("제안 조회 실패");
			}

			return await response.json();
		} catch (error) {
			console.error("제안 조회 실패:", error);
			throw error;
		}
	}

	/**
	 * 제안을 적용합니다.
	 */
	async applyProposal(
		proposalId: string,
		topicId: string
	): Promise<ProposalApplyResponse> {
		const url = `${this.plugin.settings.apiEndpoint}/proposals/apply`;

		const request: ProposalApplyRequest = {
			proposal_id: proposalId,
			topic_id: topicId,
		};

		try {
			const response = await fetch(url, {
				method: "POST",
				headers: this.getHeaders(),
				body: JSON.stringify(request),
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || "제안 적용 실패");
			}

			const data = await response.json();

			new Notice(data.message);

			return data;
		} catch (error) {
			new Notice(`제안 적용 실패: ${error}`);
			throw error;
		}
	}

	/**
	 * 제안을 거절합니다.
	 */
	async rejectProposal(proposalId: string, topicId: string): Promise<void> {
		const url = `${this.plugin.settings.apiEndpoint}/proposals/${proposalId}/reject?topic_id=${topicId}`;

		try {
			const response = await fetch(url, {
				method: "POST",
				headers: this.getHeaders(),
			});

			if (!response.ok) {
				throw new Error("제안 거절 실패");
			}

			const data = await response.json();
			new Notice(data.message);
		} catch (error) {
			new Notice(`제안 거절 실패: ${error}`);
			throw error;
		}
	}

	/**
	 * 전체 동기화 프로세스를 실행합니다.
	 */
	async fullSync(topics: Topic[]): Promise<{
		taskId: string;
		count: number;
	}> {
		// 1. 검증 요청
		const validationResponse = await this.uploadTopics(topics);

		// 2. 대기 및 상태 확인
		const taskId = validationResponse.task_id;
		let status = await this.getValidationStatus(taskId);

		// 3. 완료 대기 (폴링)
		while (status.status !== "completed" && status.status !== "failed") {
			await this.sleep(2000); // 2초 대기
			status = await this.getValidationStatus(taskId);

			// 진행률 표시
			if (status.progress !== undefined) {
				new Notice(`검증 진행 중: ${status.progress}%`);
			}
		}

		if (status.status === "failed") {
			throw new Error(`검증 실패: ${status.error}`);
		}

		// 4. 제안 생성
		const proposals = await this.generateProposals(taskId);

		return {
			taskId,
			count: proposals.length,
		};
	}

	/**
	 * 제안 내용을 마크다운 파일에 적용합니다.
	 */
	async applyProposalToFile(
		proposal: EnhancementProposal,
		topic: Topic
	): Promise<void> {
		const file = this.plugin.app.vault.getAbstractFileByPath(
			topic.metadata.file_path
		);

		if (!file || !(file instanceof TFile)) {
			throw new Error("파일을 찾을 수 없습니다.");
		}

		// 현재 내용 읽기
		let content = await this.plugin.app.vault.read(file);

		// 해당 필드 찾기 및 교체
		const fieldName = proposal.target_field;
		const pattern = new RegExp(
			`${fieldName}:\\s*([^\\n]*)`,
			"i"
		);

		// 필드가 있는지 확인
		if (pattern.test(content)) {
			// 기존 필드 업데이트
			content = content.replace(
				pattern,
				`${fieldName}: ${proposal.suggested_content}`
			);
		} else {
			// 새 필드 추가 (프론트매터나 본문에)
			// 프론트매터가 있는지 확인
			if (content.startsWith("---")) {
				// 프론트매터 뒤에 추가
				const frontmatterEnd = content.indexOf("---", 3) + 3;
				content =
					content.slice(0, frontmatterEnd) +
					`\n${fieldName}: ${proposal.suggested_content}` +
					content.slice(frontmatterEnd);
			} else {
				// 파일 시작에 프론트매터 추가
				content = `---\n${fieldName}: ${proposal.suggested_content}\n---\n\n${content}`;
			}
		}

		// 파일 업데이트
		await this.plugin.app.vault.modify(file, content);

		new Notice(`${proposal.title}이(가) 적용되었습니다.`);
	}

	/**
	 * HTTP 헤더를 생성합니다.
	 */
	private getHeaders(): Record<string, string> {
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};

		if (this.plugin.settings.apiKey) {
			headers["Authorization"] = `Bearer ${this.plugin.settings.apiKey}`;
		}

		return headers;
	}

	/**
	 * 지정된 시간(밀리초) 동안 대기합니다.
	 */
	private sleep(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
