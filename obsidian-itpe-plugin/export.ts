import { App } from "obsidian";
import ITPEPlugin from "./main";
import { Topic, DomainEnum, ExamFrequencyEnum, DataviewQueryResult } from "./types";

/**
 * Dataview JSON 내보내기 기능
 * Dataview 쿼리 실행 결과를 JSON 포맷으로 변환합니다.
 */
export class DataviewExporter {
	plugin: ITPEPlugin;
	app: App;

	constructor(plugin: ITPEPlugin) {
		this.plugin = plugin;
		this.app = plugin.app;
	}

	/**
	 * 현재 열려 있는 파일에서 Dataview 쿼리를 실행하고 결과를 JSON으로 내보냅니다.
	 */
	async exportFromCurrentFile(): Promise<DataviewQueryResult> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			throw new Error("활성 파일이 없습니다.");
		}

		const content = await this.app.vault.read(activeFile);

		// Dataview 코드 블록 추출
		const dataviewBlocks = this.extractDataviewBlocks(content);

		if (dataviewBlocks.length === 0) {
			throw new Error("Dataview 쿼리 블록을 찾을 수 없습니다.");
		}

		// 토픽 데이터 추출
		const topics: Topic[] = [];

		for (const block of dataviewBlocks) {
			const blockTopics = await this.extractTopicsFromDataview(block);
			topics.push(...blockTopics);
		}

		return {
			성공: true,
			데이터: topics,
			에러: undefined
		};
	}

	/**
	 * Markdown 내용에서 Dataview 코드 블록을 추출합니다.
	 */
	private extractDataviewBlocks(content: string): string[] {
		const blocks: string[] = [];
		const regex = /```dataview([\s\S]*?)```/g;
		let match;

		while ((match = regex.exec(content)) !== null) {
			blocks.push(match[1].trim());
		}

		return blocks;
	}

	/**
	 * Dataview 쿼리 블록에서 토픽 정보를 추출합니다.
	 * Dataview API가 있는지 확인하고 사용합니다.
	 */
	private async extractTopicsFromDataview(query: string): Promise<Topic[]> {
		// Dataview 플러그인 확인
		const dataviewPlugin = (this.app as any).plugins.plugins["dataview"];

	 if (!dataviewPlugin) {
			throw new Error("Dataview 플러그인이 설치되지 않았습니다.");
		}

		try {
			// Dataview 쿼리 실행
			const result = await dataviewPlugin.api.query(query);

			if (result.successful === false) {
				throw new Error(`Dataview 쿼리 실패: ${result.error}`);
			}

			// 결과값을 Topic 형식으로 변환
			return this.convertDataviewResultToTopics(result);
		} catch (error) {
			throw new Error(`Dataview 쿼리 실행 중 오류 발생: ${error}`);
		}
	}

	/**
	 * Dataview 쿼리 결과를 Topic 배열로 변환합니다.
	 */
	private convertDataviewResultToTopics(result: any): Topic[] {
		const topics: Topic[] = [];

		if (!result.value.values || result.value.values.length === 0) {
			return topics;
		}

		for (const row of result.value.values) {
			try {
				const topic = this.convertRowToTopic(row);
				if (topic) {
					topics.push(topic);
				}
			} catch (error) {
				console.error("토픽 변환 중 오류:", error, row);
			}
		}

		return topics;
	}

	/**
	 * Dataview 결과 행을 Topic 객체로 변환합니다.
	 */
	private convertRowToTopic(row: any): Topic | null {
		// Dataview 결과 형식에 따라 필드 추출
		// 일반적으로 row는 배열 형태이며 각 필드에 접근할 수 있습니다.

		// 파일 경로
		const file = row[0];
		if (!file) return null;

		const filePath = file.path;
		const fileName = file.name;
		const folder = this.extractFolderName(filePath);

		// 도메인 추출
		const domain = this.extractDomainFromPath(filePath);

		// 내용 추출
		const content: Topic["content"] = {
			리드문: this.extractField(row, "리드문") || "",
			정의: this.extractField(row, "정의") || "",
			키워드: this.extractKeywords(row) || [],
			해시태그: this.extractField(row, "해시태그") || "",
			암기: this.extractField(row, "암기") || ""
		};

		// 완성도 확인
		const completion: Topic["completion"] = {
			리드문: content.리드문.length > 0,
			정의: content.정의.length > 0,
			키워드: content.키워드.length > 0,
			해시태그: content.해시태그.length > 0,
			암기: content.암기.length > 0
		};

		// Topic ID 생성 (파일 경로 기반)
		const id = this.generateTopicId(filePath);

		return {
			id,
			metadata: {
				file_path: filePath,
				file_name: fileName,
				folder,
				domain,
				exam_frequency: ExamFrequencyEnum.MEDIUM
			},
			content,
			completion,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		};
	}

	/**
	 * 파일 경로에서 폴더 이름을 추출합니다.
	 */
	private extractFolderName(filePath: string): string {
		const parts = filePath.split("/");
		if (parts.length >= 2) {
			return parts[parts.length - 2];
		}
		return "";
	}

	/**
	 * 파일 경로에서 도메인을 추출합니다.
	 */
	private extractDomainFromPath(filePath: string): DomainEnum {
		const domainMapping = this.plugin.settings.domainMapping;

		// 경로에 포함된 도메인 폴더 찾기
		for (const [folderName, domain] of Object.entries(domainMapping)) {
			if (filePath.includes(folderName)) {
				return domain;
			}
		}

		// 기본값
		return DomainEnum.신기술;
	}

	/**
	 * Dataview 결과 행에서 특정 필드를 추출합니다.
	 */
	private extractField(row: any, fieldName: string): string {
		// Dataview 결과 형식: 다양한 필드 위치 확인
		for (let i = 0; i < row.length; i++) {
			const value = row[i];
			if (value && typeof value === "object") {
				// 객체인 경우 필드 확인
				if (fieldName in value) {
					return String(value[fieldName]);
				}
			}
		}
		return "";
	}

	/**
	 * Dataview 결과 행에서 키워드를 추출합니다.
	 */
	private extractKeywords(row: any): string[] {
		const keywordsField = this.extractField(row, "키워드");

		if (!keywordsField) {
			return [];
		}

		// 쉼표 또는 대괄호로 구분된 키워드 처리
		if (keywordsField.startsWith("[")) {
			try {
				return JSON.parse(keywordsField.replace(/'/g, '"'));
			} catch {
				// 파싱 실패 시 쉼표로 분리
				return keywordsField
					.replace(/[\[\]]/g, "")
					.split(",")
					.map((k) => k.trim())
					.filter((k) => k.length > 0);
			}
		}

		return keywordsField.split(",").map((k) => k.trim()).filter((k) => k.length > 0);
	}

	/**
	 * 파일 경로에서 토픽 ID를 생성합니다.
	 */
	private generateTopicId(filePath: string): string {
		// 경로를 기반으로 고유 ID 생성
		return filePath
			.toLowerCase()
			.replace(/[^a-z0-9]/g, "-")
			.replace(/-+/g, "-")
			.replace(/^-|-$/g, "");
	}

	/**
	 * 토픽 데이터를 JSON으로 클립보드에 복사합니다.
	 */
	async copyToClipboard(topics: Topic[]): Promise<void> {
		const json = JSON.stringify(topics, null, 2);
		await navigator.clipboard.writeText(json);
	}

	/**
	 * 토픽 데이터를 JSON 파일로 저장합니다.
	 */
	async saveToFile(topics: Topic[], filename: string = "itpe-topics.json"): Promise<void> {
		const json = JSON.stringify(topics, null, 2);
		const filepath = `${filename}`;

		await this.app.vault.create(filepath, json);
	}
}
